"""CarValue application API (FastAPI).

Public valuation endpoints and admin routes. Domain logic lives in ``carvalue_core``;
this package owns HTTP boundaries, settings, sessions, and CLI commands.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import Any

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SqlAlchemySession, sessionmaker

import carvalue_core.persistence as persistence
from carvalue_core.confidence import ConfidenceLabel, EvidenceConfig
from carvalue_core.models import ValuationModel, evaluate_prediction
from carvalue_core.persistence import (
    AdminSession,
    AdminUser,
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
from carvalue_core.security import (
    create_admin_session,
    record_audit_event,
    revoke_admin_session,
    validate_admin_session,
    verify_csrf_token,
    verify_password,
)

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

app.state.db_url = "sqlite:///./data/carvalue.db"  # default; overwritten by cli/tests


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Response:
    """Inject strict security headers across all API responses (PRD Section 11)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    )
    return response


@app.get("/")
def root_status() -> dict[str, Any]:
    """Root entry point providing discovery links."""
    return {
        "service": "CarValue API",
        "description": "Explainable used-pickup asking-price valuator for Alberta, Canada",
        "version": "0.1.0",
        "interactive_docs": "/docs",
        "openapi_schema": "/openapi.json",
        "endpoints": {
            "taxonomy": "/v1/taxonomy",
            "system_status": "/v1/system/status",
            "valuations": "/v1/valuations",
            "feedback": "/v1/valuations/feedback",
            "admin_login": "/admin/login",
        },
    }


def get_db() -> SqlAlchemySession:
    engine = persistence.make_engine(app.state.db_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


# ---------------------------------------------------------------------------
# Admin Auth & CSRF Dependencies
# ---------------------------------------------------------------------------


def get_current_admin(
    carvalue_admin_session: str | None = Cookie(default=None),
) -> tuple[AdminSession, AdminUser]:
    """Validate authenticated admin session from secure cookie."""
    if not carvalue_admin_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    db = get_db()
    try:
        res = validate_admin_session(db, carvalue_admin_session)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired admin session",
            )
        admin_sess, user = res
        db.commit()
        return admin_sess, user
    finally:
        db.close()


def require_csrf(
    request: Request,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
    x_csrf_token: str | None = Header(default=None),
) -> None:
    """Enforce CSRF token verification on state-changing requests."""
    admin_sess, _ = auth
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        if not x_csrf_token or not verify_csrf_token(admin_sess, x_csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing CSRF token",
            )


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class ValuationRequest(BaseModel):
    make: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=1990, le=2035)
    mileage_km: int = Field(..., ge=0, le=800_000)
    trim: str | None = Field(default=None)
    category: str | None = Field(default=None)  # "pickup" | "suv" | "sedan" | "hatchback" | "van" | "coupe" | "all"
    drivetrain: str | None = Field(default=None)  # "2wd" | "4wd"
    seller_type: str | None = Field(default=None)  # "dealer" | "private"
    region: str | None = Field(default=None)  # "calgary_region" | "edmonton_region" etc.
    dataset_filter: str | None = Field(default="all")  # "all" | "real_only" | "synthetic_only"

    @field_validator("make", "model")
    @classmethod
    def _non_empty(cls, v: Any) -> Any:
        if isinstance(v, str):
            val = v.strip()
            if val:
                return val
        raise ValueError("must be a non-empty string")


class ValuationFeedbackRequest(BaseModel):
    valuation_event_id: int | None = Field(default=None)
    feedback_useful: bool
    feedback_notes: str | None = Field(default=None, max_length=500)


class ValuationResponse(BaseModel):
    estimate_cad: int  # rounded to nearest $100 CAD
    interval_low_cad: int
    interval_high_cad: int
    confidence_label: str  # high | medium | low | insufficient_data
    comparables_count: int
    real_comparables_count: int = 0
    synthetic_comparables_count: int = 0
    dataset_provenance: str = "Real Alberta Dealer Listings (2022)"
    data_freshness_days: float
    valuation_date: date
    disclaimer: str = "This is an estimate, not a professional appraisal."


class TaxonomyResponse(BaseModel):
    makes: list[str] = Field(default_factory=list)
    models_by_make: dict[str, list[str]] = Field(default_factory=dict)
    trims_by_model: dict[str, list[str]] = Field(default_factory=dict)
    categories: list[str] = Field(default_factory=lambda: ["pickup", "suv", "sedan", "hatchback", "van", "coupe", "wagon", "all"])
    models_by_category: dict[str, dict[str, list[str]]] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    email: str
    display_name: str | None
    csrf_token: str


class CreateSnapshotRequest(BaseModel):
    label: str = Field(..., min_length=1)
    description: str | None = Field(default=None)


class ResolveIssueRequest(BaseModel):
    action: str = Field(..., pattern="^(resolved|dismissed)$")
    notes: str | None = Field(default=None)


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


@app.get("/healthz", tags=["system"])
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.get("/v1/system/status", tags=["system"])
async def system_status() -> dict[str, Any]:
    """Return operational system health, active model version, and market data freshness."""
    db = get_db()
    try:
        active_model = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active").limit(1)
        ).scalar_one_or_none()

        listings_count = db.execute(select(func.count(Listing.id))).scalar_one()
        comps_count = db.execute(select(func.count(ListingPriceHistory.id))).scalar_one()

        real_listings_count = db.execute(
            select(func.count(Listing.id))
            .join(Source, Source.id == Listing.source_id)
            .where(Source.name == "ca-dealers-used-2022")
        ).scalar() or 0
        synthetic_listings_count = int(listings_count) - int(real_listings_count)

        latest_obs = db.execute(select(func.max(ListingPriceHistory.observed_at))).scalar_one()
        if latest_obs:
            freshness_days = max(float((datetime.now(UTC).date() - latest_obs.date()).days), 0.0)
        else:
            freshness_days = float("inf")

        return {
            "status": "ok",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "active_model": (
                {
                    "id": active_model.id,
                    "algorithm": active_model.algorithm,
                    "trained_at_utc": active_model.trained_at_utc.isoformat(),
                    "metrics": active_model.metrics_json,
                }
                if active_model
                else None
            ),
            "data_freshness_days": freshness_days if freshness_days != float("inf") else None,
            "total_listings": int(listings_count),
            "total_price_observations": int(comps_count),
            "sources_breakdown": {
                "real_dealer_listings_2022": int(real_listings_count),
                "synthetic_simulator_sample": int(synthetic_listings_count),
            },
        }
    finally:
        db.close()


@app.post(
    "/v1/valuations",
    response_model=ValuationResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate an Alberta pickup asking price.",
)
async def valuation(request: ValuationRequest, req: Request) -> ValuationResponse:
    """Return an explainable asking-price estimate for a supported vehicle."""
    start_time = time.perf_counter()
    db = get_db()
    try:
        ref_header = req.headers.get("x-valuation-date")
        if ref_header:
            try:
                val_date = date.fromisoformat(ref_header[:10])
            except ValueError:
                val_date = date.today()
        else:
            val_date = date.today()

        make_canonical = resolve_make(db, request.make) or request.make.strip()
        model_canonical = (
            resolve_model(db, make_canonical, request.model) or request.model.strip()
        )
        trim_canonical = (
            resolve_trim(db, make_canonical, model_canonical, request.trim)
            if (make_canonical and model_canonical and request.trim)
            else (request.trim.strip() if request.trim else None)
        )
        drivetrain_canonical = (
            request.drivetrain if request.drivetrain in ("2wd", "4wd") else None
        )
        seller_type_canonical = (
            request.seller_type if request.seller_type in ("dealer", "private") else None
        )

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
                real_comparables_count=0,
                synthetic_comparables_count=0,
                dataset_provenance="Insufficient Evidence",
                data_freshness_days=float("inf"),
                valuation_date=val_date,
            )

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
                real_comparables_count=0,
                synthetic_comparables_count=0,
                dataset_provenance="Model Error",
                data_freshness_days=float("inf"),
                valuation_date=val_date,
            )

        comp_query = (
            select(ListingPriceHistory, Source.name.label("source_name"))
            .join(Listing, Listing.id == ListingPriceHistory.listing_id)
            .join(Source, Source.id == Listing.source_id)
            .where(
                Listing.make == make_canonical,
                Listing.model == model_canonical,
                Listing.is_active.is_(True),
            )
        )
        if request.dataset_filter == "real_only":
            comp_query = comp_query.where(Source.name == "ca-dealers-used-2022")
        elif request.dataset_filter == "synthetic_only":
            comp_query = comp_query.where(Source.name != "ca-dealers-used-2022")

        all_comp_rows = db.execute(comp_query).all()
        comps = [r[0] for r in all_comp_rows if r[0].observed_at.date() <= val_date]
        real_comps_count = sum(
            1 for r in all_comp_rows if r[1] == "ca-dealers-used-2022" and r[0].observed_at.date() <= val_date
        )
        synthetic_comps_count = len(comps) - real_comps_count
        comparables_count = len(comps)

        if comps:
            latest_observed = max(c.observed_at.date() for c in comps)
            data_freshness_days = max(float((val_date - latest_observed).days), 0.0)
        else:
            data_freshness_days = float("inf")

        features = {
            "model_year": request.year,
            "mileage_km": request.mileage_km,
            "trim": trim_canonical,
            "drivetrain": drivetrain_canonical,
            "seller_type": seller_type_canonical,
            "valuation_date": val_date,
        }
        point_raw, low_raw, high_raw = model.predict(features)

        config = (
            EvidenceConfig(stale_after_days=2500)
            if request.dataset_filter in ("real_only", "all")
            else None
        )
        decision = evaluate_prediction(
            point_cad=point_raw,
            low_cad=low_raw,
            high_cad=high_raw,
            features=features,
            model=model,
            comparables_count=comparables_count,
            data_freshness_days=data_freshness_days,
            config=config,
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

        _log_valuation_event(
            db=db,
            request=request,
            req=req,
            model_version_id=model_row.id,
            confidence_label=decision.label,
            comparables_count=comparables_count,
            latency_ms=latency_ms,
        )

        if request.dataset_filter == "real_only":
            provenance = "Real Alberta Dealer Listings (2022 Dataset)"
        elif request.dataset_filter == "synthetic_only":
            provenance = "Simulated Benchmark Sample"
        else:
            if real_comps_count > 0 and synthetic_comps_count > 0:
                provenance = f"Combined Evidence ({real_comps_count} Real, {synthetic_comps_count} Simulated)"
            elif real_comps_count > 0:
                provenance = "Real Alberta Dealer Listings (2022 Dataset)"
            else:
                provenance = "Simulated Benchmark Sample"

        return ValuationResponse(
            estimate_cad=est_cad,
            interval_low_cad=low_cad,
            interval_high_cad=high_cad,
            confidence_label=decision.label,
            comparables_count=comparables_count,
            real_comparables_count=real_comps_count,
            synthetic_comparables_count=synthetic_comps_count,
            dataset_provenance=provenance,
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


@app.post("/v1/valuations/feedback", tags=["valuation"])
async def submit_valuation_feedback(payload: ValuationFeedbackRequest) -> dict[str, Any]:
    """Record visitor feedback on asking price estimate (PRD FR-OBS-02)."""
    db = get_db()
    try:
        if payload.valuation_event_id:
            event = db.get(ValuationEvent, payload.valuation_event_id)
            if event:
                event.feedback_useful = payload.feedback_useful
                db.commit()
                return {
                    "ok": True,
                    "event_id": event.id,
                    "feedback_useful": event.feedback_useful,
                }

        # If no event ID provided, create feedback event
        new_event = ValuationEvent(
            occurred_at=datetime.now(UTC),
            event_type="feedback",
            feedback_useful=payload.feedback_useful,
            input_json={"notes": payload.feedback_notes} if payload.feedback_notes else {},
            confidence_label="feedback",
            comparables_count=0,
            interval_level=80,
            latency_ms=0,
            device_class="web",
        )
        db.add(new_event)
        db.commit()
        return {
            "ok": True,
            "event_id": new_event.id,
            "feedback_useful": payload.feedback_useful,
        }
    finally:
        db.close()


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
        models_by_category: dict[str, dict[str, list[str]]] = {}

        for n in nodes:
            if n.level == "model" and n.parent_id:
                parent = db.get(VehicleTaxonomy, n.parent_id)
                if parent:
                    make_name = parent.canonical_name
                    models_by_make.setdefault(make_name, []).append(n.canonical_name)
                    raw_cat = n.aliases_json[1] if (n.aliases_json and len(n.aliases_json) > 1) else "other"
                    cat = str(raw_cat or "other").strip().lower()
                    models_by_category.setdefault(cat, {}).setdefault(make_name, []).append(n.canonical_name)
            elif n.level == "trim" and n.parent_id:
                model_parent = db.get(VehicleTaxonomy, n.parent_id)
                if model_parent and model_parent.parent_id:
                    make_parent = db.get(VehicleTaxonomy, model_parent.parent_id)
                    if make_parent:
                        key = f"{make_parent.canonical_name}:{model_parent.canonical_name}"
                        trims_by_model.setdefault(key, []).append(n.canonical_name)

        categories = ["pickup", "suv", "sedan", "hatchback", "van", "coupe", "wagon", "all"]

        return TaxonomyResponse(
            makes=makes,
            models_by_make=models_by_make,
            trims_by_model=trims_by_model,
            categories=categories,
            models_by_category=models_by_category,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin routes (Session Authenticated & CSRF Protected)
# ---------------------------------------------------------------------------


@app.post("/admin/login", response_model=LoginResponse, tags=["admin"])
async def admin_login(
    payload: LoginRequest, req: Request, response: Response
) -> LoginResponse:
    """Authenticate admin and issue 12-hour session + CSRF cookies."""
    db = get_db()
    try:
        user = db.execute(
            select(AdminUser).where(AdminUser.email == payload.email)
        ).scalar_one_or_none()

        if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
            record_audit_event(
                session=db,
                actor_type="system",
                actor_ref=payload.email,
                action="admin.login_failed",
                outcome="blocked",
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        ua = req.headers.get("user-agent", "")
        admin_sess, raw_token, raw_csrf = create_admin_session(
            session=db,
            user=user,
            duration_hours=12,
            user_agent_coarse=ua,
        )
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="admin.login",
            target_type="admin_user",
            target_ref=str(user.id),
            outcome="ok",
        )
        db.commit()

        # Set secure session and CSRF cookies
        response.set_cookie(
            key="carvalue_admin_session",
            value=raw_token,
            max_age=43200,
            httponly=True,
            samesite="lax",
            path="/admin",
        )
        response.set_cookie(
            key="carvalue_admin_csrf",
            value=raw_csrf,
            max_age=43200,
            httponly=False,
            samesite="lax",
            path="/admin",
        )

        return LoginResponse(
            email=user.email,
            display_name=user.display_name,
            csrf_token=raw_csrf,
        )
    finally:
        db.close()


@app.post("/admin/logout", tags=["admin"])
async def admin_logout(
    response: Response,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
    carvalue_admin_session: str | None = Cookie(default=None),
) -> dict[str, bool]:
    """Revoke admin session and clear authentication cookies."""
    db = get_db()
    try:
        _, user = auth
        if carvalue_admin_session:
            revoke_admin_session(db, carvalue_admin_session)
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="admin.logout",
            outcome="ok",
        )
        db.commit()

        response.delete_cookie("carvalue_admin_session", path="/admin")
        response.delete_cookie("carvalue_admin_csrf", path="/admin")
        return {"ok": True}
    finally:
        db.close()


@app.get("/admin/me", tags=["admin"])
async def admin_me(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Return profile for currently authenticated admin."""
    _, user = auth
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
    }


@app.get("/admin/audit", tags=["admin"])
async def audit_log(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = (
            db.execute(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(200))
            .scalars()
            .all()
        )
        return [
            {
                "occurred_at": row.occurred_at.isoformat(),
                "actor_type": row.actor_type,
                "actor_ref": row.actor_ref,
                "action": row.action,
                "target_type": row.target_type,
                "target_ref": row.target_ref,
                "outcome": row.outcome,
                "details_json": row.details_json,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.get("/admin/sources", tags=["admin"])
async def list_sources(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
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
                "policy_reviewed_at": (
                    row.policy_reviewed_at.isoformat() if row.policy_reviewed_at else None
                ),
            }
            for row in rows
        ]
    finally:
        db.close()


@app.post(
    "/admin/sources/{source_id}/toggle",
    dependencies=[Depends(require_csrf)],
    tags=["admin"],
)
async def toggle_source(
    source_id: int,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Toggle enabled status of a source."""
    db = get_db()
    try:
        _, user = auth
        source = db.get(Source, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        source.enabled = not source.enabled
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="source.toggle",
            target_type="source",
            target_ref=str(source_id),
            outcome="ok",
            details_json={"enabled": source.enabled},
        )
        db.commit()
        return {"id": source.id, "name": source.name, "enabled": source.enabled}
    finally:
        db.close()


@app.get("/admin/models", tags=["admin"])
async def list_models(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
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
                "artifact_path": row.artifact_path,
                "model_hash_sha256": row.model_hash_sha256,
            }
            for row in rows
        ]
    finally:
        db.close()


@app.post(
    "/admin/models/{model_id}/promote",
    dependencies=[Depends(require_csrf)],
    tags=["admin"],
)
async def promote_model(
    model_id: int,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Promote a model version to active status (PRD FR-ADM-04, FR-ML-09)."""
    db = get_db()
    try:
        _, user = auth
        target = db.get(ModelVersion, model_id)
        if not target:
            raise HTTPException(status_code=404, detail="Model version not found")

        # Archive current active models
        active_models = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active")
        ).scalars().all()
        for m in active_models:
            m.status = "retired"

        target.status = "active"
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="model.promote",
            target_type="model_version",
            target_ref=str(model_id),
            outcome="ok",
            details_json={"algorithm": target.algorithm},
        )
        db.commit()
        return {"id": target.id, "algorithm": target.algorithm, "status": target.status}
    finally:
        db.close()


@app.post(
    "/admin/models/{model_id}/rollback",
    dependencies=[Depends(require_csrf)],
    tags=["admin"],
)
async def rollback_model(
    model_id: int,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Roll back model promotion and restore a target model version."""
    db = get_db()
    try:
        _, user = auth
        target = db.get(ModelVersion, model_id)
        if not target:
            raise HTTPException(status_code=404, detail="Model version not found")

        active_models = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active")
        ).scalars().all()
        for m in active_models:
            m.status = "retired"

        target.status = "active"
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="model.rollback",
            target_type="model_version",
            target_ref=str(model_id),
            outcome="ok",
            details_json={"algorithm": target.algorithm},
        )
        db.commit()
        return {"id": target.id, "algorithm": target.algorithm, "status": target.status}
    finally:
        db.close()


@app.get("/admin/taxonomy", tags=["admin"])
async def admin_taxonomy(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
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
async def list_snapshots(
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    db = get_db()
    try:
        rows = db.execute(select(DatasetSnapshot)).scalars().all()
        return [
            {
                "id": row.id,
                "label": row.label,
                "row_count": row.row_count,
                "content_checksum_sha256": row.content_checksum_sha256,
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


@app.post(
    "/admin/dataset-snapshots",
    dependencies=[Depends(require_csrf)],
    tags=["admin"],
)
async def create_snapshot(
    payload: CreateSnapshotRequest,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Create a frozen dataset snapshot record (PRD FR-ADM-04, FR-ML-09)."""
    db = get_db()
    try:
        _, user = auth
        listings = db.execute(
            select(ListingPriceHistory).order_by(ListingPriceHistory.id.asc())
        ).scalars().all()

        row_count = len(listings)
        min_observed = min((l.observed_at for l in listings), default=None)
        max_observed = max((l.observed_at for l in listings), default=None)

        # Compute checksum across dataset
        hasher = hashlib.sha256()
        for l in listings:
            hasher.update(
                f"{l.id}:{l.asking_price_cad_cents}:{l.observed_at.isoformat()}".encode()
            )
        checksum = hasher.hexdigest()

        snapshot = DatasetSnapshot(
            label=payload.label,
            definition_json={"filter": "alberta_pickups", "description": payload.description or ""},
            row_count=row_count,
            min_observed_at=min_observed,
            max_observed_at=max_observed,
            content_checksum_sha256=checksum,
        )
        db.add(snapshot)
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="dataset.snapshot_created",
            target_type="dataset_snapshot",
            target_ref=payload.label,
            outcome="ok",
            details_json={"row_count": row_count, "checksum": checksum},
        )
        db.commit()
        return {
            "id": snapshot.id,
            "label": snapshot.label,
            "row_count": snapshot.row_count,
            "content_checksum_sha256": snapshot.content_checksum_sha256,
        }
    finally:
        db.close()


@app.get("/admin/listings", tags=["admin"])
async def list_listings(
    limit: int = 100,
    offset: int = 0,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    db = get_db()
    try:
        total = db.execute(select(func.count(Listing.id))).scalar_one()
        rows = db.execute(select(Listing).offset(offset).limit(limit)).scalars().all()
        return {
            "total": int(total),
            "listings": [
                {
                    "id": row.id,
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
async def listing_price_history(
    listing_id: int,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
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
async def data_quality_issues(
    status_filter: str | None = None,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    db = get_db()
    try:
        query = select(DataQualityIssue)
        if status_filter:
            query = query.where(DataQualityIssue.status == status_filter)
        rows = db.execute(query).scalars().all()
        return {
            "issues": [
                {
                    "id": row.id,
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


@app.post(
    "/admin/data-quality/{issue_id}/resolve",
    dependencies=[Depends(require_csrf)],
    tags=["admin"],
)
async def resolve_data_quality_issue(
    issue_id: int,
    payload: ResolveIssueRequest,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Resolve or dismiss a flagged data quality issue."""
    db = get_db()
    try:
        _, user = auth
        issue = db.get(DataQualityIssue, issue_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found")
        issue.status = payload.action
        issue.reviewer = user.email
        issue.resolved_at = datetime.now(UTC)
        record_audit_event(
            session=db,
            actor_type="admin",
            actor_ref=user.email,
            action="data_quality.resolve",
            target_type="data_quality_issue",
            target_ref=str(issue_id),
            outcome="ok",
            details_json={"status": payload.action, "notes": payload.notes},
        )
        db.commit()
        return {"id": issue.id, "status": issue.status}
    finally:
        db.close()


@app.get("/admin/valuation-events", tags=["admin"])
async def valuation_events(
    limit: int = 100,
    auth: tuple[AdminSession, AdminUser] = Depends(get_current_admin),
) -> dict[str, Any]:
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
                    "latency_ms": row.latency_ms,
                    "feedback_useful": row.feedback_useful,
                }
                for row in rows
            ],
        }
    finally:
        db.close()
