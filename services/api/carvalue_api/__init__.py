"""CarValue application API (FastAPI).

Public valuation endpoints and admin routes. Domain logic lives in ``carvalue_core``;
this package owns HTTP boundaries, settings, sessions, and CLI commands.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import Any

import carvalue_core.persistence as persistence
from carvalue_core.confidence import ConfidenceLabel
from carvalue_core.models import ValuationModel, evaluate_prediction
from carvalue_core.persistence import (
    AuditEvent,
    DataQualityIssue,
    DatasetSnapshot,
    Listing,
    ListingPriceHistory,
    ModelVersion,
    Source,
    ValuationEvent,
    VehicleTaxonomy,
    resolve_make,
    resolve_model,
    resolve_trim,
)
from fastapi import FastAPI, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SqlAlchemySession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings and app wiring (Lifespan)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ensure database exists on startup."""
    if app.state.db_url:
        engine = persistence.make_engine(app.state.db_url)
        try:
            persistence.Base.metadata.create_all(bind=engine)
        except Exception as exc:
            logger.warning("Database create_all skipped: %s", exc)
        finally:
            engine.dispose()
    yield


app = FastAPI(
    title="CarValue API",
    description="Explainable used-pickup asking-price valuator for Alberta, Canada.",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.db_url = "sqlite:///./carvalue.db"  # default; overwritten by cli/tests


def get_db() -> SqlAlchemySession:
    engine = persistence.make_engine(app.state.db_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class ValuationRequest(BaseModel):
    make: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=2010, le=2035)
    mileage_km: int = Field(..., ge=0, le=800_000)
    trim: str | None = Field(default=None)
    drivetrain: str | None = Field(default=None)  # "2wd" | "4wd"
    seller_type: str | None = Field(default=None)  # "dealer" | "private"

    @field_validator("make", "model")
    @classmethod
    def _non_empty(cls, v: Any) -> Any:
        if isinstance(v, str):
            val = v.strip()
            if val:
                return val
        raise ValueError("must be a non-empty string")


class ValuationResponse(BaseModel):
    estimate_cad: int  # rounded to nearest $100 CAD
    interval_low_cad: int
    interval_high_cad: int
    confidence_label: str  # high | medium | low | insufficient_data
    comparables_count: int
    data_freshness_days: float
    valuation_date: date
    disclaimer: str = "This is an estimate, not a professional appraisal."


class TaxonomyResponse(BaseModel):
    makes: list[str] = Field(default_factory=list)
    models_by_make: dict[str, list[str]] = Field(default_factory=dict)
    trims_by_model: dict[str, list[str]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["system"])
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post(
    "/v1/valuations",
    response_model=ValuationResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate an Alberta pickup asking price.",
)
async def valuation(request: ValuationRequest, req: Request) -> ValuationResponse:
    """Return an explainable asking-price estimate for a supported vehicle.

    The result is an **asking-price estimate**, not an appraisal or guaranteed
    sale price. It includes an 80% prediction interval, confidence label,
    comparable count, data freshness, and a clear disclaimer. Out-of-distribution
    inputs are refused with ``insufficient_data`` rather than fabricated precision.
    """
    start_time = time.perf_counter()
    db = get_db()
    try:
        # 1. Parse valuation date
        ref_header = req.headers.get("x-valuation-date")
        if ref_header:
            try:
                val_date = date.fromisoformat(ref_header[:10])
            except ValueError:
                val_date = date.today()
        else:
            val_date = date.today()

        # 2. Resolve taxonomy
        make_canonical = resolve_make(db, request.make)
        model_canonical = (
            resolve_model(db, make_canonical, request.model) if make_canonical else None
        )
        trim_canonical = (
            resolve_trim(db, make_canonical, model_canonical, request.trim)
            if (make_canonical and model_canonical and request.trim)
            else None
        )
        drivetrain_canonical = request.drivetrain if request.drivetrain in ("2wd", "4wd") else None
        seller_type_canonical = (
            request.seller_type if request.seller_type in ("dealer", "private") else None
        )

        # 3. Load active model
        model_row = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active").limit(1)
        ).scalar_one_or_none()

        if not make_canonical or not model_canonical or not model_row:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            _log_valuation_event(
                db=db,
                request=request,
                req=req,
                model_version_id=model_row.id if model_row else None,
                confidence_label=ConfidenceLabel.INSUFFICIENT_DATA,
                comparables_count=0,
                latency_ms=latency_ms,
            )
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label=ConfidenceLabel.INSUFFICIENT_DATA,
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=val_date,
            )

        # 4. Load model artifact
        try:
            model = ValuationModel.load(model_row.artifact_path)
        except Exception as exc:
            logger.error("Failed to load model artifact %s: %s", model_row.artifact_path, exc)
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label=ConfidenceLabel.INSUFFICIENT_DATA,
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=val_date,
            )

        # 5. Query active comparables
        comp_query = (
            select(ListingPriceHistory)
            .join(Listing, Listing.id == ListingPriceHistory.listing_id)
            .where(
                Listing.make == make_canonical,
                Listing.model == model_canonical,
                Listing.is_active.is_(True),
            )
        )
        all_comps = db.execute(comp_query).scalars().all()
        comps = [c for c in all_comps if c.observed_at.date() <= val_date]
        comparables_count = len(comps)

        if comps:
            latest_observed = max(c.observed_at.date() for c in comps)
            data_freshness_days = max(float((val_date - latest_observed).days), 0.0)
        else:
            data_freshness_days = float("inf")

        # 6. Predict point and 80% interval
        features = {
            "model_year": request.year,
            "mileage_km": request.mileage_km,
            "trim": trim_canonical,
            "drivetrain": drivetrain_canonical,
            "seller_type": seller_type_canonical,
            "valuation_date": val_date,
        }
        point_raw, low_raw, high_raw = model.predict(features)

        # 7. Evaluate confidence / refusal
        decision = evaluate_prediction(
            point_cad=point_raw,
            low_cad=low_raw,
            high_cad=high_raw,
            features=features,
            model=model,
            comparables_count=comparables_count,
            data_freshness_days=data_freshness_days,
        )

        if decision.is_refused:
            est_cad = 0
            low_cad = 0
            high_cad = 0
        else:
            est_cad = int(round(point_raw / 100.0) * 100)
            low_cad = int(round(low_raw / 100.0) * 100)
            high_cad = int(round(high_raw / 100.0) * 100)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 8. Record telemetry
        _log_valuation_event(
            db=db,
            request=request,
            req=req,
            model_version_id=model_row.id,
            confidence_label=decision.label,
            comparables_count=comparables_count,
            latency_ms=latency_ms,
        )

        return ValuationResponse(
            estimate_cad=est_cad,
            interval_low_cad=low_cad,
            interval_high_cad=high_cad,
            confidence_label=decision.label,
            comparables_count=comparables_count,
            data_freshness_days=round(data_freshness_days, 1),
            valuation_date=val_date,
        )
    finally:
        db.close()


def _log_valuation_event(
    db: SqlAlchemySession,
    request: ValuationRequest,
    req: Request,
    model_version_id: int | None,
    confidence_label: str,
    comparables_count: int,
    latency_ms: int,
) -> None:
    """Record a privacy-minimized visitor event (FR-OBS-01)."""
    try:
        ua = req.headers.get("user-agent", "").lower()
        device = "mobile" if "mobile" in ua else "desktop"
        event = ValuationEvent(
            occurred_at=datetime.now(UTC),
            event_type="valuation",
            input_json={
                "make": request.make,
                "model": request.model,
                "year": request.year,
                "mileage_km": request.mileage_km,
                "trim": request.trim,
                "drivetrain": request.drivetrain,
                "seller_type": request.seller_type,
            },
            model_version_id=model_version_id,
            confidence_label=confidence_label,
            comparables_count=comparables_count,
            interval_level=80,
            latency_ms=latency_ms,
            device_class=device,
            visitor_id=req.headers.get("x-visitor-id"),
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to record valuation event: %s", exc)


@app.get("/v1/taxonomy", response_model=TaxonomyResponse)
async def taxonomy() -> TaxonomyResponse:
    """Return the supported make/model/trim reference data."""
    db = get_db()
    try:
        nodes = (
            db.execute(select(VehicleTaxonomy).where(VehicleTaxonomy.active.is_(True)))
            .scalars()
            .all()
        )

        makes = sorted({n.canonical_name for n in nodes if n.level == "make"})
        models_by_make: dict[str, list[str]] = {}
        trims_by_model: dict[str, list[str]] = {}

        for n in nodes:
            if n.level == "model" and n.parent_id:
                parent = db.get(VehicleTaxonomy, n.parent_id)
                if parent:
                    models_by_make.setdefault(parent.canonical_name, []).append(n.canonical_name)
            elif n.level == "trim" and n.parent_id:
                model_parent = db.get(VehicleTaxonomy, n.parent_id)
                if model_parent and model_parent.parent_id:
                    make_parent = db.get(VehicleTaxonomy, model_parent.parent_id)
                    if make_parent:
                        key = f"{make_parent.canonical_name}:{model_parent.canonical_name}"
                        trims_by_model.setdefault(key, []).append(n.canonical_name)

        return TaxonomyResponse(
            makes=makes,
            models_by_make=models_by_make,
            trims_by_model=trims_by_model,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@app.get("/admin/audit", tags=["admin"])
async def audit_log() -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(AuditEvent)).scalars().all()
        return [
            {
                "occurred_at": row.occurred_at.isoformat(),
                "actor_type": row.actor_type,
                "action": row.action,
                "target_type": row.target_type,
                "outcome": row.outcome,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/sources", tags=["admin"])
async def list_sources() -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(Source)).scalars().all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "source_type": row.source_type,
                "permission_status": row.permission_status,
                "enabled": row.enabled,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/models", tags=["admin"])
async def list_models() -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(ModelVersion)).scalars().all()
        return [
            {
                "id": row.id,
                "algorithm": row.algorithm,
                "status": row.status,
                "trained_at_utc": row.trained_at_utc.isoformat(),
                "metrics_json": row.metrics_json,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/taxonomy", tags=["admin"])
async def admin_taxonomy() -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(VehicleTaxonomy)).scalars().all()
        return [
            {
                "level": row.level,
                "canonical_name": row.canonical_name,
                "aliases_json": row.aliases_json,
                "active": row.active,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/dataset-snapshots", tags=["admin"])
async def list_snapshots() -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(DatasetSnapshot)).scalars().all()
        return [
            {
                "label": row.label,
                "row_count": row.row_count,
                "min_observed_at_utc": (
                    row.min_observed_at.isoformat() if row.min_observed_at else None
                ),
                "max_observed_at_utc": (
                    row.max_observed_at.isoformat() if row.max_observed_at else None
                ),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/listings", tags=["admin"])
async def list_listings(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    try:
        total = db.execute(select(func.count(Listing.id))).scalar_one()
        rows = db.execute(select(Listing).offset(offset).limit(limit)).scalars().all()
        return {
            "total": int(total),
            "listings": [
                {
                    "make": row.make,
                    "model": row.model,
                    "trim": row.trim,
                    "drivetrain": row.drivetrain,
                    "seller_type": row.seller_type,
                    "mileage_km": int(row.mileage_km),
                    "asking_price_cad_cents": int(row.asking_price_cad_cents),
                    "first_seen_at_utc": row.first_seen_at.isoformat(),
                }
                for row in rows
            ],
        }
    finally:
        db.close()


@app.get("/admin/listings/{listing_id}/price-history", tags=["admin"])
async def listing_price_history(listing_id: int) -> dict[str, Any]:
    db = get_db()
    try:
        rows = (
            db.execute(
                select(ListingPriceHistory).where(ListingPriceHistory.listing_id == listing_id)
            )
            .scalars()
            .all()
        )
        return {
            "listing_id": int(listing_id),
            "history": [
                {
                    "observed_at_utc": r.observed_at.isoformat(),
                    "asking_price_cad_cents": int(r.asking_price_cad_cents),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


@app.get("/admin/data-quality", tags=["admin"])
async def data_quality_issues(status_filter: str | None = None) -> dict[str, Any]:
    db = get_db()
    try:
        query = select(DataQualityIssue)
        if status_filter:
            query = query.where(DataQualityIssue.status == status_filter)
        rows = db.execute(query).scalars().all()
        return {
            "issues": [
                {
                    "listing_id": int(row.listing_id) if row.listing_id is not None else None,
                    "source_record_ref": row.source_record_ref,
                    "reason_code": row.reason_code,
                    "status": row.status,
                }
                for row in rows
            ],
        }
    finally:
        db.close()


@app.get("/admin/valuation-events", tags=["admin"])
async def valuation_events(limit: int = 100) -> dict[str, Any]:
    db = get_db()
    try:
        total = db.execute(select(func.count(ValuationEvent.id))).scalar_one()
        rows = (
            db.execute(
                select(ValuationEvent).order_by(ValuationEvent.occurred_at.desc()).limit(limit)
            )
            .scalars()
            .all()
        )
        return {
            "total": int(total),
            "events": [
                {
                    "occurred_at_utc": row.occurred_at.isoformat(),
                    "event_type": row.event_type,
                    "confidence_label": row.confidence_label,
                    "comparables_count": row.comparables_count,
                    "feedback_useful": row.feedback_useful,
                }
                for row in rows
            ],
        }
    finally:
        db.close()
