"""SQLAlchemy persistence models and SQLite conventions (PRD section 8).

Conventions:
- Money is integer CAD cents (``BigInteger``); never binary float currency.
- Timestamps are UTC, stored as ISO-8601 ``...Z`` strings via :class:`UtcTimestamp`.
- SQLite runs with WAL mode, foreign keys enabled, and a busy timeout; every
  schema change goes through an Alembic migration (see services/api/migrations).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.types import TypeDecorator

from .listings import ListingObservation, UpsertOutcome, listing_fingerprint
from .reasons import ReasonCode


def utcnow() -> datetime:
    """Current UTC timestamp (tz-aware)."""
    return datetime.now(timezone.utc)


class UtcTimestamp(TypeDecorator):
    """UTC timestamps stored as ISO-8601 ``Z`` strings; loaded tz-aware."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def process_result_value(self, value: str | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed


class Base(DeclarativeBase):
    """Declarative base for all CarValue tables."""


# ---------------------------------------------------------------------------
# Sources, schedules and runs (ingestion boundary)
# ---------------------------------------------------------------------------


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual_import"
    )  # manual_import | api_feed | crawler | open_data
    base_url: Mapped[str | None] = mapped_column(String(512))
    #: Permission gate (FR-DATA-02): only "approved" may run automated collection.
    permission_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    policy_reviewed_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    policy_review_due: Mapped[date | None] = mapped_column(Date)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer)
    adapter_name: Mapped[str | None] = mapped_column(String(64))  # e.g. csv_import, playwright
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UtcTimestamp, nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        CheckConstraint("permission_status IN ('approved','unknown','denied')", name="ck_source_perm"),
        CheckConstraint(
            "source_type IN ('manual_import','api_feed','crawler','open_data')", name="ck_source_type"
        ),
    )


class CrawlSchedule(Base):
    __tablename__ = "crawl_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), unique=True, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)
    #: IANA time zone; Alberta services use "America/Edmonton" (AGENTS.md).
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Edmonton")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    last_run_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_schedules.id"))
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    started_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    finished_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    parser_version: Mapped[str | None] = mapped_column(String(16))
    error_summary: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','succeeded','partially_succeeded','failed','cancelled')",
            name="ck_crawl_run_state",
        ),
        # Database-backed lease (FR-ADM-04): at most one queued/running run per source.
        Index(
            "uq_crawl_runs_active_per_source",
            "source_id",
            unique=True,
            sqlite_where=text("state IN ('queued','running')"),
        ),
    )


class RawObservation(Base):
    """Latest raw-content reference per source record (retention-gated)."""

    __tablename__ = "raw_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_runs.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(1024))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    #: Filesystem reference to compressed raw body, when retained at all.
    body_ref: Mapped[str | None] = mapped_column(String(512))
    fetched_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    retention_expires_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)

    __table_args__ = (UniqueConstraint("source_id", "source_record_id"),)


# ---------------------------------------------------------------------------
# Normalized listings and price history
# ---------------------------------------------------------------------------


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(1024))
    fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    make: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    trim: Mapped[str | None] = mapped_column(String(64))
    drivetrain: Mapped[str | None] = mapped_column(String(8))  # 2wd | 4wd
    seller_type: Mapped[str | None] = mapped_column(String(16))  # dealer | private
    cab_style: Mapped[str | None] = mapped_column(String(32))
    box_length_m: Mapped[float | None] = mapped_column()
    province: Mapped[str] = mapped_column(String(8), nullable=False, default="AB")
    city: Mapped[str | None] = mapped_column(String(120))

    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage_km: Mapped[int] = mapped_column(BigInteger, nullable=False)
    asking_price_cad_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    #: Observation time of the current price on this listing row.
    price_observed_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parser_version: Mapped[str] = mapped_column(String(16), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UtcTimestamp, nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_listing_source_record"),
        CheckConstraint("mileage_km >= 0", name="ck_listing_mileage_non_negative"),
        CheckConstraint("asking_price_cad_cents > 0", name="ck_listing_price_positive"),
        CheckConstraint("model_year BETWEEN 1900 AND 2100", name="ck_listing_model_year_range"),
        CheckConstraint(
            "drivetrain IS NULL OR drivetrain IN ('2wd','4wd')", name="ck_listing_drivetrain"
        ),
        CheckConstraint(
            "seller_type IS NULL OR seller_type IN ('dealer','private')", name="ck_listing_seller"
        ),
        Index("ix_listings_make_model", "make", "model"),
        # Dedup step 2: a canonical URL identifies one listing across sources.
        Index(
            "uq_listings_canonical_url",
            "canonical_url",
            unique=True,
            sqlite_where=text("canonical_url IS NOT NULL"),
        ),
    )


class ListingPriceHistory(Base):
    """Append-only asking-price observations per listing (never overwritten)."""

    __tablename__ = "listing_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    asking_price_cad_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    raw_observation_id: Mapped[int | None] = mapped_column(ForeignKey("raw_observations.id"))

    __table_args__ = (
        UniqueConstraint("listing_id", "observed_at", name="uq_price_history_listing_time"),
        CheckConstraint("asking_price_cad_cents > 0", name="ck_price_history_positive"),
        Index("ix_price_history_listing_time", "listing_id", "observed_at"),
    )


# ---------------------------------------------------------------------------
# Taxonomy, quality, snapshots and models
# ---------------------------------------------------------------------------


class VehicleTaxonomy(Base):
    __tablename__ = "vehicle_taxonomy"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(8), nullable=False)  # make | model | trim
    canonical_name: Mapped[str] = mapped_column(String(64), nullable=False)
    aliases_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("vehicle_taxonomy.id"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("level IN ('make','model','trim')", name="ck_taxonomy_level"),
        UniqueConstraint(
            "level", "parent_id", "canonical_name", name="uq_taxonomy_entry"
        ),
    )


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("crawl_runs.id"))
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id"))
    source_record_ref: Mapped[str | None] = mapped_column(String(256))
    reason_code: Mapped[str] = mapped_column(String(48), nullable=False)
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    reviewer: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)

    __table_args__ = (
        CheckConstraint("status IN ('open','resolved','dismissed')", name="ck_dqi_status"),
    )


class DatasetSnapshot(Base):
    """Immutable training-data definition + row counts + content checksum."""

    __tablename__ = "dataset_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    definition_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    min_observed_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    max_observed_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    content_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. ols_baseline
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    feature_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    data_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_snapshots.id"))
    code_revision: Mapped[str | None] = mapped_column(String(64))
    trained_at_utc: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    model_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate','active','retired','rejected')", name="ck_model_status"
        ),
        # Promotion is explicit: at most one active model exists.
        Index(
            "uq_model_versions_single_active",
            "id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )


# ---------------------------------------------------------------------------
# Visitor analytics and admin/audit
# ---------------------------------------------------------------------------


class ValuationEvent(Base):
    """Privacy-minimized valuation/feedback events (no personal identity)."""

    __tablename__ = "valuation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(12), nullable=False, default="valuation")
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"))
    confidence_label: Mapped[str | None] = mapped_column(String(20))
    comparables_count: Mapped[int | None] = mapped_column(Integer)
    interval_level: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    device_class: Mapped[str | None] = mapped_column(String(16))  # desktop|mobile|other (coarse)
    visitor_id: Mapped[str | None] = mapped_column(String(64))  # pseudonymous, rotating
    feedback_useful: Mapped[bool | None] = mapped_column(Boolean)
    expected_transaction_price_cad_cents: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        CheckConstraint("event_type IN ('valuation','feedback')", name="ck_valuation_event_type"),
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    revoked_at: Mapped[datetime | None] = mapped_column(UtcTimestamp)
    user_agent_coarse: Mapped[str | None] = mapped_column(String(32))


class AuditEvent(Base):
    """Append-only admin mutation trail (actor, time, action, target, outcome)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcTimestamp, nullable=False, default=utcnow)
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False, default="system")  # admin|system
    actor_ref: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_ref: Mapped[str | None] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(8), nullable=False, default="ok")
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("actor_type IN ('admin','system')", name="ck_audit_actor"),
        CheckConstraint("outcome IN ('ok','error','blocked')", name="ck_audit_outcome"),
    )


# ---------------------------------------------------------------------------
# Engine setup and upsert semantics
# ---------------------------------------------------------------------------

SQLITE_BUSY_TIMEOUT_MS = 5000


def make_engine(url: str) -> Engine:
    """Create the engine with CarValue's SQLite conventions applied.

    WAL mode, foreign keys enabled, and a busy timeout (AGENTS.md). Non-SQLite
    URLs (future PostgreSQL migration path) are returned unmodified aside from
    pooling defaults.
    """
    from sqlalchemy import create_engine

    engine = create_engine(url, future=True)
    if url.startswith("sqlite"):
        _attach_sqlite_pragmas(engine)
    return engine


def _attach_sqlite_pragmas(engine: Engine) -> None:
    @listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")
            cursor.execute("PRAGMA foreign_keys=ON;")
        finally:
            cursor.close()


def new_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _as_utc(value: object) -> datetime:
    """Coerce a loosely-typed timestamp to tz-aware UTC (observed_at_utc is typed
    loose on purpose to avoid a core↔persistence import cycle)."""
    if not isinstance(value, datetime):
        raise TypeError(f"expected datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def upsert_listing_observation(session: Session, obs: ListingObservation) -> UpsertOutcome:
    """Idempotently apply one normalized observation (FR-DATA-05/06).

    - New listing: insert + first price-history point; status ``accepted``.
    - Known (source, source_record_id): refresh last-seen and attributes; append a
      price-history point at the new observation time when it is not already
      recorded; status ``updated`` or ``duplicate`` accordingly.
    - Cross-source fingerprint/URL collisions are flagged in data_quality_issues
      without merging (conservative deduplication).
    """
    from sqlalchemy import select

    observed_at = _as_utc(obs.observed_at_utc)
    fingerprint = listing_fingerprint(obs)

    existing = session.execute(
        select(Listing).where(
            Listing.source_id == obs.source_id,
            Listing.source_record_id == obs.source_record_id,
        )
    ).scalar_one_or_none()

    # Latest raw-content reference per record (checksum/fetch time refreshed on re-import).
    raw = session.execute(
        select(RawObservation).where(
            RawObservation.source_id == obs.source_id,
            RawObservation.source_record_id == obs.source_record_id,
        )
    ).scalar_one_or_none()
    if raw is None:
        raw = RawObservation(
            source_id=obs.source_id,
            source_record_id=obs.source_record_id,
            canonical_url=obs.canonical_url,
            content_checksum_sha256=obs.content_checksum_sha256,
            fetched_at=observed_at,
        )
        session.add(raw)
    else:
        raw.fetched_at = observed_at
        if obs.content_checksum_sha256 is not None:
            raw.content_checksum_sha256 = obs.content_checksum_sha256

    history_appended = False
    if existing is None:
        clash = session.execute(
            select(Listing.id).where(Listing.fingerprint_sha256 == fingerprint)
        ).first()
        listing = Listing(
            source_id=obs.source_id,
            source_record_id=obs.source_record_id,
            canonical_url=obs.canonical_url,
            fingerprint_sha256=fingerprint,
            make=obs.make,
            model=obs.model,
            trim=obs.trim,
            drivetrain=obs.drivetrain,
            seller_type=obs.seller_type,
            cab_style=obs.cab_style,
            box_length_m=obs.box_length_m,
            province=obs.province,
            city=obs.city,
            model_year=obs.model_year,
            mileage_km=obs.mileage_km,
            asking_price_cad_cents=obs.asking_price_cad_cents,
            price_observed_at=observed_at,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            parser_version=obs.parser_version,
        )
        session.add(listing)
        session.flush()  # assigns listing.id
        history_appended = True
        if clash is not None:
            session.add(
                DataQualityIssue(
                    listing_id=listing.id,
                    source_record_ref=f"{obs.source_id}:{obs.source_record_id}",
                    reason_code=ReasonCode.POSSIBLE_DUPLICATE.value,
                    detail_json={"matched_listing_id": int(clash[0])},
                )
            )
        return UpsertOutcome(status="accepted", listing_id=listing.id, price_history_appended=True)

    changed = False
    new_last_seen = max(existing.last_seen_at, observed_at)
    if new_last_seen != existing.last_seen_at:
        existing.last_seen_at = new_last_seen
        changed = True

    if obs.mileage_km != existing.mileage_km:
        existing.mileage_km = obs.mileage_km
        changed = True
    for field_name in ("trim", "drivetrain", "seller_type", "cab_style"):
        new_value = getattr(obs, field_name)
        if new_value is not None and getattr(existing, field_name) != new_value:
            setattr(existing, field_name, new_value)
            changed = True

    existing_price_history_time = session.execute(
        select(ListingPriceHistory.id).where(
            ListingPriceHistory.listing_id == existing.id,
            ListingPriceHistory.observed_at == observed_at,
        )
    ).first()
    price_changed = obs.asking_price_cad_cents != existing.asking_price_cad_cents
    if existing_price_history_time is None:
        session.add(
            ListingPriceHistory(
                listing_id=existing.id,
                observed_at=observed_at,
                asking_price_cad_cents=obs.asking_price_cad_cents,
                raw_observation_id=raw.id,
            )
        )
        history_appended = True
        changed = True

    if price_changed:
        existing.asking_price_cad_cents = obs.asking_price_cad_cents
        existing.price_observed_at = observed_at
        changed = True

    status = "updated" if changed else "duplicate"
    return UpsertOutcome(status=status, listing_id=existing.id, price_history_appended=history_appended)


def resolve_make(db: Session, raw: object) -> str | None:
    """Resolve a raw make string to its canonical form (None when unknown).

    Uses the same normalization as the in-memory taxonomy so import and valuation
    paths agree on canonical values (FR-PUB-01). Queries the ``vehicle_taxonomy``
    table, not a free-text allowlist.
    """
    from .taxonomy import normalize_token

    if raw is None:
        return None
    rows = db.execute(
        select(VehicleTaxonomy).where(
            VehicleTaxonomy.level == "make",
            VehicleTaxonomy.active.is_(True),
        )
    ).scalars().all()
    for row in rows:
        names = [row.canonical_name, *[str(a) for a in row.aliases_json]]
        if any(normalize_token(raw) == normalize_token(name) for name in names):
            return row.canonical_name
    return None


def resolve_model(db: Session, make_canonical: str, raw: object) -> str | None:
    """Resolve a model name within one canonical make (None when unknown)."""
    from .taxonomy import normalize_token

    if raw is None:
        return None
    rows = db.execute(
        select(VehicleTaxonomy).where(
            VehicleTaxonomy.level == "model",
            VehicleTaxonomy.parent_id.isnot(None),
            VehicleTaxonomy.active.is_(True),
        )
    ).scalars().all()
    for row in rows:
        parent = db.get(VehicleTaxonomy, row.parent_id)
        if parent is None or parent.canonical_name != make_canonical:
            continue
        names = [row.canonical_name, *[str(a) for a in row.aliases_json]]
        if any(normalize_token(raw) == normalize_token(name) for name in names):
            return row.canonical_name
    return None


def resolve_trim(db: Session, make_canonical: str, model_canonical: str, raw: object) -> str | None:
    """Resolve a trim name within one canonical model (None when unknown)."""
    from .taxonomy import normalize_token

    if raw is None:
        return None
    rows = db.execute(
        select(VehicleTaxonomy).where(
            VehicleTaxonomy.level == "trim",
            VehicleTaxonomy.parent_id.isnot(None),
            VehicleTaxonomy.active.is_(True),
        )
    ).scalars().all()
    for row in rows:
        parent = db.get(VehicleTaxonomy, row.parent_id)
        if parent is None or parent.canonical_name != model_canonical:
            continue
        names = [row.canonical_name, *[str(a) for a in row.aliases_json]]
        if any(normalize_token(raw) == normalize_token(name) for name in names):
            return row.canonical_name
    return None


def dump_json_stable(value: Any) -> str:
    """Deterministic JSON serialization (checksums, artifacts)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
