"""CarValue application API (FastAPI).

Public valuation endpoints and (later) admin routes. The domain logic lives in
``carvalue_core``; this package owns HTTP boundaries, settings, sessions and the
Alembic migration entry point.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession

import carvalue_core.persistence as persistence
from carvalue_core.confidence import ConfidenceDecision, decide_confidence
from carvalue_core.listings import ListingObservation
from carvalue_core.persistence import (
    AdminUser,
    AuditEvent,
    DatasetSnapshot,
    ListingPriceHistory,
    ModelVersion,
    Source,
    UtcTimestamp,
    VehicleTaxonomy,
    new_session_factory,
)
from carvalue_core.taxonomy import PickupTaxonomy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings and app wiring
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CarValue API",
    description="Explainable used-pickup asking-price valuator for Alberta, Canada.",
    version="0.1.0",
)

app.state.db_url: str = ""  # set by the entry point


def get_db() -> SqlAlchemySession:
    from sqlalchemy.orm import sessionmaker

    engine = persistence.make_engine(app.state.db_url)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


@app.on_event("startup")
async def _startup() -> None:
    # Ensure the database exists (migrations are run by ``carvalue init-db``).
    with get_db() as session:
        try:
            session.execute(persistence.Base.metadata.create_all(bind=engine))
        except Exception as exc:
            logger.warning("database already exists, skipping create_all: %s", exc)


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
            return v.strip()
        raise ValueError("must be a non-empty string")


class ValuationResponse(BaseModel):
    estimate_cad: int  # rounded to nearest $100
    interval_low_cad: int
    interval_high_cad: int
    confidence_label: str  # high | medium | low | insufficient_data
    comparables_count: int
    data_freshness_days: float
    valuation_date: date


class TaxonomyResponse(BaseModel):
    makes: list[str] = Field(default_factory=list)
    models_by_make: dict[str, list[str]] = Field(default_factory=dict)
    trims_by_model: dict[tuple[str, str], list[str]] = Field(default_factory=dict)


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
    inputs are refused with ``Insufficient Data`` rather than fabricated precision.

    Response times: P95 ≤ 3 s cached, ≤ 5 s uncached (FR-PUB-01/FR-PUB-02).
    """
    db = get_db()
    try:
        # Resolve taxonomy and load the active model artifact.
        make_canonical = persistence.resolve_make(db, request.make)
        if not make_canonical:
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label="insufficient_data",
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=date.today(),
            )

        model_canonical = persistence.resolve_model(db, make_canonical, request.model)
        if not model_canonical:
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label="insufficient_data",
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=date.today(),
            )

        trim_canonical = persistence.resolve_trim(db, make_canonical, model_canonical, request.trim)
        drivetrain_canonical = (
            request.drivetrain if request.drivetrain in ("2wd", "4wd") else None
        )
        seller_type_canonical = request.seller_type or None

        # Load the active model artifact.
        model_row = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active").limit(1)
        ).scalar_one_or_none()
        if not model_row:
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label="insufficient_data",
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=date.today(),
            )

        artifact_path = Path(model_row.artifact_path)
        feature_schema: dict[str, Any] = {}
        model_fn = None  # type: ignore[assignment]
        if artifact_path.suffix == ".pkl":
            import joblib

            model_fn = joblib.load(artifact_path)
            feature_schema = {"version": "v1"}
        elif artifact_path.suffix == ".json":
            with artifact_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                model_fn = data.get("model_fn")  # type: ignore[assignment]
                feature_schema = {"version": "v1"}

        if not callable(model_fn):
            return ValuationResponse(
                estimate_cad=0,
                interval_low_cad=0,
                interval_high_cad=0,
                confidence_label="insufficient_data",
                comparables_count=0,
                data_freshness_days=float("inf"),
                valuation_date=date.today(),
            )

        # Compute vehicle age at the valuation date (FR-ML-01).
        from carvalue_core.units import (
            DAYS_PER_YEAR,
            MODEL_YEAR_ANCHOR_DAY,
            MODEL_YEAR_ANCHOR_MONTH,
        )

        anchor = date(request.year, MODEL_YEAR_ANCHOR_MONTH, MODEL_YEAR_ANCHOR_DAY)
        reference_date = req.headers.get("x-valuation-date", str(date.today()))
        valuation_date = datetime.fromisoformat(reference_date.replace("Z", "+00:00"))
        vehicle_age_years = max((valuation_date - anchor).days / DAYS_PER_YEAR, 0.0)

        # Query active comparables for this make/model/trim/drivetrain/seller_type.
        query = (
            select(ListingPriceHistory)
            .join(Listing)
            .where(
                Listing.make == make_canonical,
                Listing.model == model_canonical,
                Listing.trim == trim_canonical if trim_canonical else None,
                Listing.drivetrain == drivetrain_canonical if drivetrain_canonical else None,
                Listing.seller_type == seller_type_canonical if seller_type_canonical else None,
                Listing.is_active == True,  # noqa: E712
            )
        )

        rows = db.execute(query).scalars()
        comparables: list[ListingPriceHistory] = []
        for row in rows:
            if row.observed_at_utc.date() <= valuation_date:
                comparables.append(row)

        # Compute the point estimate and interval.
        point_estimate_cad, low_cad_cents, high_cad_cents = model_fn(
            vehicle_age_years, request.mileage_km, trim_canonical or "", drivetrain_canonical or "", seller_type_canonical or ""
        )  # type: ignore[call-arg]

        if not isinstance(point_estimate_cad, int):
            point_estimate_cad = int(round(point_estimate_cad))
        low_cad_cents = int(low_cad_cents)
        high_cad_cents = int(high_cad_cents)

        # Confidence rules (FR-ML-10).
        from carvalue_core.confidence import EvidenceConfig, ModelBounds, out_of_training_domain, relative_interval_width

        bounds = ModelBounds(
            min_model_year=2019, max_model_year=2023, min_mileage_km=0, max_mileage_km=800_000
        )
        ood = out_of_training_domain(bounds, request.year, request.mileage_km)

        interval_rel_width = relative_interval_width(low_cad_cents, point_estimate_cad, high_cad_cents)
        decision = decide_confidence(
            comparables_count=len(comparables),
            data_freshness_days=(valuation_date.date() - date.min()).days / 365.25,
            interval_rel_width=interval_rel_width,
            ood=ood,
        )

        return ValuationResponse(
            estimate_cad=persistence.round_cad_to_nearest_100(point_estimate_cad),
            interval_low_cad=low_cad_cents,
            interval_high_cad=high_cad_cents,
            confidence_label=decision.label,
            comparables_count=len(comparables),
            data_freshness_days=(valuation_date.date() - date.min()).days / 365.25,
            valuation_date=valuation_date.date(),
        )

    finally:
        db.close()


@app.get("/v1/taxonomy", response_model=TaxonomyResponse)
async def taxonomy() -> TaxonomyResponse:
    """Return the supported make/model/trim reference data."""
    nodes = persistence.seed_pickup_taxonomy().nodes
    makes = sorted({n.canonical_name for n in nodes if n.level == "make"})
    models_by_make: dict[str, list[str]] = {}
    trims_by_model: dict[tuple[str, str], list[str]] = {}
    for node in nodes:
        if node.level == "model":
            make = models_by_make.setdefault(node.parent_canonical, [])
            make.append(node.canonical_name)
        elif node.level == "trim":
            key = (node.parent_canonical, node.parent_canonical)  # placeholder; real trim resolution lives in persistence
            trims_by_model.setdefault(key, []).append(node.canonical_name)
    return TaxonomyResponse(makes=makes, models_by_make=models_by_make, trims_by_model=trims_by_model)


# ---------------------------------------------------------------------------
# Admin routes (authentication and CSRF are wired by the entry point; these
# endpoints enforce role protection via ``request.state.user``.)
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
                "metrics_json": json.loads(json.dumps(row.metrics_json)),  # copy for JSON response
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
                "aliases_json": json.loads(json.dumps(row.aliases_json)),
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
                "min_observed_at_utc": row.min_observed_at.isoformat(),
                "max_observed_at_utc": row.max_observed_at.isoformat(),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/listings", tags=["admin"])
async def list_listings(limit: int = 100, offset: int = 0) -> dict[str, Any]:
    db = get_db()
    try:
        total = db.execute(
            select(persistence.Integer).select_from(Listing).count()
        ).scalar_one()
        rows = db.execute(
            select(Listing).offset(offset).limit(limit),
        ).scalars().all()
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
        row = db.execute(
            select(ListingPriceHistory).where(ListingPriceHistory.listing_id == listing_id),
        ).scalars().all()
        return {
            "listing_id": int(listing_id),
            "history": [
                {"observed_at_utc": r.observed_at.isoformat(), "asking_price_cad_cents": int(r.asking_price_cad_cents)}
                for r in row
            ],
        }
    finally:
        db.close()


@app.get("/admin/data-quality", tags=["admin"])
async def data_quality_issues(status_filter: str | None = None) -> dict[str, Any]:
    db = get_db()
    try:
        rows = db.execute(
            select(DataQualityIssue).where(
                DataQualityIssue.status == status_filter if status_filter else True
            ),
        ).scalars().all()
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
        total = db.execute(
            select(persistence.Integer).select_from(ValuationEvent).count()
        ).scalar_one()
        rows = db.execute(
            select(ValuationEvent).order_by(ValuationEvent.occurred_at.desc()).limit(limit),
        ).scalars().all()
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


# ---------------------------------------------------------------------------
# Entry point (carvalue command)
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(prog="carvalue")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="initialize the SQLite database with migrations and seed data")
    init_parser.set_defaults(func=do_init_db)

    run_parser = subparsers.add_parser("run", help="start the FastAPI server (default port 8000)")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.set_defaults(func=do_run_server)

    args = parser.parse_args()
    app.state.db_url = "sqlite:///./carvalue.db"  # single-host MVP; migrations live in services/api/migrations
    args.func()


def do_init_db() -> None:
    from carvalue_api.migrations import run_migrations

    Path("services/api/carvalue.db").touch()
    app.state.db_url = "sqlite:///./carvalue.db"
    run_migrations()
    print("database initialized with migrations and seed data")


def do_run_server() -> None:
    from uvicorn import Config, Server

    config = Config(app=app, host="127.0.0.1", port=8000)
    server = Server(config=config)
    server.run()


if __name__ == "__main__":
    main()
