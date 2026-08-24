"""Launch hardening, security headers, backup/restore, and retention tests for M7."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_api.maintenance import (
    backup_database,
    purge_expired_retention,
    restore_database,
)
from carvalue_core.persistence import (
    AdminSession,
    AdminUser,
    AuditEvent,
    Listing,
    ListingPriceHistory,
    ModelVersion,
    RawObservation,
    Source,
    make_engine,
    new_session_factory,
)
from carvalue_core.security import hash_password, hash_token


@pytest.fixture
def hardened_db(tmp_path: Path) -> str:
    db_path = tmp_path / "hardened_test.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)

    engine = make_engine(db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        # Seed Source
        source = Source(
            name="test_source",
            source_type="api_feed",
            permission_status="approved",
            enabled=True,
        )
        session.add(source)
        session.flush()

        # Seed Active Model
        m = ModelVersion(
            algorithm="ols_baseline",
            status="active",
            artifact_path="/tmp/m.joblib",
            feature_schema_json={},
            metrics_json={"mae_cad": 1100.0},
            trained_at_utc=datetime(2026, 8, 20, tzinfo=UTC),
            model_hash_sha256="hash123",
        )
        session.add(m)
        session.flush()

        # Seed Listing & Price History
        listing = Listing(
            source_id=source.id,
            source_record_id="rec-1",
            fingerprint_sha256="fp-1",
            make="ford",
            model="ranger",
            model_year=2022,
            mileage_km=30000,
            asking_price_cad_cents=3200000,
            price_observed_at=datetime(2026, 8, 15, tzinfo=UTC),
            first_seen_at=datetime(2026, 8, 15, tzinfo=UTC),
            last_seen_at=datetime(2026, 8, 15, tzinfo=UTC),
        )
        session.add(listing)
        session.flush()

        ph = ListingPriceHistory(
            listing_id=listing.id,
            asking_price_cad_cents=3200000,
            observed_at=datetime(2026, 8, 15, tzinfo=UTC),
        )
        session.add(ph)

        # Seed Raw Observations: one recent, one expired (100 days old)
        now = datetime.now(UTC)
        raw_recent = RawObservation(
            source_id=source.id,
            source_record_id="rec-recent",
            fetched_at=now - timedelta(days=10),
            content_checksum_sha256="recent_hash",
        )
        raw_expired = RawObservation(
            source_id=source.id,
            source_record_id="rec-old",
            fetched_at=now - timedelta(days=100),
            content_checksum_sha256="old_hash",
        )
        session.add_all([raw_recent, raw_expired])

        # Use existing Admin User from do_init_db
        admin = session.execute(select(AdminUser)).scalars().first()
        admin_id = admin.id if admin else 1

        sess_active = AdminSession(
            admin_user_id=admin_id,
            token_hash=hash_token("tok_active"),
            csrf_token_hash=hash_token("csrf_active"),
            created_at=now,
            expires_at=now + timedelta(hours=12),
        )
        sess_expired = AdminSession(
            admin_user_id=admin_id,
            token_hash=hash_token("tok_expired"),
            csrf_token_hash=hash_token("csrf_expired"),
            created_at=now - timedelta(days=50),
            expires_at=now - timedelta(days=45),
        )
        session.add_all([sess_active, sess_expired])

        session.commit()
    engine.dispose()
    return db_url


def test_security_headers_injected_across_endpoints(hardened_db: str) -> None:
    """PRD Section 11: Security headers must be present on API responses."""
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200

    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-xss-protection"] == "1; mode=block"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers["content-security-policy"]


def test_system_status_endpoint(hardened_db: str) -> None:
    """Verify /v1/system/status returns active model, freshness, and listing totals."""
    client = TestClient(app)
    response = client.get("/v1/system/status")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["active_model"]["algorithm"] == "ols_baseline"
    assert data["total_listings"] == 1
    assert data["total_price_observations"] == 1
    assert data["data_freshness_days"] is not None


def test_database_backup_and_restoration_drill(hardened_db: str, tmp_path: Path) -> None:
    """Verify online point-in-time SQLite backup and restoration."""
    backup_file = tmp_path / "backup_snapshot.db"

    # 1. Take Backup
    backup_info = backup_database(db_url=hardened_db, backup_dest_path=str(backup_file))
    assert backup_file.exists()
    assert backup_info["file_size_bytes"] > 0
    assert len(backup_info["checksum_sha256"]) == 64

    # 2. Restore Backup to a new target database
    restored_db_file = tmp_path / "restored_target.db"
    restored_db_url = f"sqlite:///{restored_db_file}"
    restore_info = restore_database(backup_src_path=str(backup_file), target_db_url=restored_db_url)
    assert restore_info["integrity"] == "ok"

    # 3. Verify restored contents
    engine = make_engine(restored_db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        listings = session.execute(select(Listing)).scalars().all()
        assert len(listings) == 1
        assert listings[0].make == "ford"

        models = session.execute(select(ModelVersion)).scalars().all()
        assert len(models) == 1
        assert models[0].status == "active"
    engine.dispose()


def test_retention_purge_job(hardened_db: str) -> None:
    """PRD Section 10/11: Purge raw observations >90d and expired sessions >30d."""
    engine = make_engine(hardened_db)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        # Before purge
        raw_count_before = len(session.execute(select(RawObservation)).scalars().all())
        sess_count_before = len(session.execute(select(AdminSession)).scalars().all())
        assert raw_count_before == 2
        assert sess_count_before == 2

        # Execute Purge
        counts = purge_expired_retention(
            session=session,
            raw_observation_retention_days=90,
            expired_session_retention_days=30,
        )

        assert counts["raw_observations_purged"] == 1
        assert counts["admin_sessions_purged"] == 1

        # Verify active records remained intact
        raw_remaining = session.execute(select(RawObservation)).scalars().all()
        assert len(raw_remaining) == 1
        assert raw_remaining[0].source_record_id == "rec-recent"

        sess_remaining = session.execute(select(AdminSession)).scalars().all()
        assert len(sess_remaining) == 1
        assert sess_remaining[0].token_hash == hash_token("tok_active")

        # Verify Audit Event was logged
        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "maintenance.retention_purge")
        ).scalars().all()
        assert len(events) == 1
        assert events[0].details_json["raw_observations_purged"] == 1

    engine.dispose()
