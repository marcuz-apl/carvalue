"""Integration tests for Admin API endpoints, authentication, CSRF defense, and governance."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_core.persistence import (
    AdminUser,
    AuditEvent,
    DataQualityIssue,
    DatasetSnapshot,
    Listing,
    ListingPriceHistory,
    ModelVersion,
    Source,
    make_engine,
    new_session_factory,
)
from carvalue_core.security import hash_password


@pytest.fixture
def admin_db(tmp_path: Path) -> str:
    """Initialize database and seed admin user."""
    db_path = tmp_path / "admin_api_test.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)

    engine = make_engine(db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        # Create known admin
        admin = AdminUser(
            email="admin@carvalue.ca",
            password_hash=hash_password("SuperSecretAdmin123!"),
            display_name="Operations Manager",
            is_active=True,
        )
        session.add(admin)
        session.commit()
    engine.dispose()
    return db_url


def test_unauthenticated_requests_return_401(admin_db: str) -> None:
    client = TestClient(app)
    endpoints = [
        "/admin/me",
        "/admin/audit",
        "/admin/sources",
        "/admin/models",
        "/admin/taxonomy",
        "/admin/dataset-snapshots",
        "/admin/listings",
        "/admin/data-quality",
        "/admin/valuation-events",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 401, f"{ep} did not enforce 401"


def test_admin_login_success_and_cookies(admin_db: str) -> None:
    client = TestClient(app)
    payload = {"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"}
    response = client.post("/admin/login", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@carvalue.ca"
    assert "csrf_token" in data
    assert "carvalue_admin_session" in response.cookies
    assert "carvalue_admin_csrf" in response.cookies


def test_admin_login_invalid_credentials_rejected(admin_db: str) -> None:
    client = TestClient(app)
    response = client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


def test_admin_logout_clears_session(admin_db: str) -> None:
    client = TestClient(app)
    # Login
    login_res = client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"},
    )
    csrf_token = login_res.json()["csrf_token"]

    # Logout
    logout_res = client.post("/admin/logout", headers={"x-csrf-token": csrf_token})
    assert logout_res.status_code == 200

    # Subsequent request should now be 401
    me_res = client.get("/admin/me")
    assert me_res.status_code == 401


def test_csrf_protection_on_mutations(admin_db: str) -> None:
    client = TestClient(app)
    client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"},
    )

    # Missing CSRF header -> 403 Forbidden
    res_no_csrf = client.post("/admin/dataset-snapshots", json={"label": "snap-2026"})
    assert res_no_csrf.status_code == 403

    # Invalid CSRF header -> 403 Forbidden
    res_bad_csrf = client.post(
        "/admin/dataset-snapshots",
        json={"label": "snap-2026"},
        headers={"x-csrf-token": "bad_token_value"},
    )
    assert res_bad_csrf.status_code == 403


def test_model_promotion_and_rollback_flow(admin_db: str) -> None:
    """PRD FR-ADM-04, FR-ML-09: explicit, audited model promotion and rollback."""
    engine = make_engine(admin_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        m1 = ModelVersion(
            algorithm="ols_baseline",
            status="active",
            artifact_path="/tmp/m1.pkl",
            feature_schema_json={},
            metrics_json={"mae_cad": 1400.0},
            trained_at_utc=datetime.now(UTC),
            model_hash_sha256="hash1",
        )
        m2 = ModelVersion(
            algorithm="catboost_candidate",
            status="candidate",
            artifact_path="/tmp/m2.pkl",
            feature_schema_json={},
            metrics_json={"mae_cad": 1150.0},
            trained_at_utc=datetime.now(UTC),
            model_hash_sha256="hash2",
        )
        session.add_all([m1, m2])
        session.commit()
        m1_id = m1.id
        m2_id = m2.id
    engine.dispose()

    client = TestClient(app)
    login_res = client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"},
    )
    csrf_token = login_res.json()["csrf_token"]

    # 1. Promote M2 (CatBoost candidate)
    prom_res = client.post(
        f"/admin/models/{m2_id}/promote",
        headers={"x-csrf-token": csrf_token},
    )
    assert prom_res.status_code == 200
    assert prom_res.json()["status"] == "active"

    # Verify M1 was retired and M2 is now active in DB
    engine = make_engine(admin_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        m1_db = session.get(ModelVersion, m1_id)
        m2_db = session.get(ModelVersion, m2_id)
        assert m1_db.status == "retired"
        assert m2_db.status == "active"

        # Check audit event
        audit = session.execute(
            select(AuditEvent).where(AuditEvent.action == "model.promote")
        ).scalar_one()
        assert audit.actor_ref == "admin@carvalue.ca"
        assert audit.target_ref == str(m2_id)
    engine.dispose()

    # 2. Rollback to M1
    roll_res = client.post(
        f"/admin/models/{m1_id}/rollback",
        headers={"x-csrf-token": csrf_token},
    )
    assert roll_res.status_code == 200
    assert roll_res.json()["status"] == "active"

    with SessionLocal() as session:
        m1_db = session.get(ModelVersion, m1_id)
        m2_db = session.get(ModelVersion, m2_id)
        assert m1_db.status == "active"
        assert m2_db.status == "retired"
    engine.dispose()


def test_create_dataset_snapshot_and_audit(admin_db: str) -> None:
    """PRD FR-ADM-04: snapshot creation records row count and checksum."""
    client = TestClient(app)
    login_res = client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"},
    )
    csrf_token = login_res.json()["csrf_token"]

    snap_res = client.post(
        "/admin/dataset-snapshots",
        json={"label": "snapshot-aug-2026", "description": "Benchmark baseline snapshot"},
        headers={"x-csrf-token": csrf_token},
    )
    assert snap_res.status_code == 200
    data = snap_res.json()
    assert data["label"] == "snapshot-aug-2026"
    assert "content_checksum_sha256" in data

    # Verify audit event was logged
    engine = make_engine(admin_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "dataset.snapshot_created")
        ).scalars().all()
        assert len(events) == 1
        assert events[0].actor_ref == "admin@carvalue.ca"
    engine.dispose()


def test_source_toggle_and_data_quality_resolution(admin_db: str) -> None:
    engine = make_engine(admin_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        source = Source(
            id=10,
            name="toggle_test_source",
            source_type="api_feed",
            permission_status="approved",
            enabled=True,
        )
        issue = DataQualityIssue(
            id=20,
            source_record_ref="rec-123",
            reason_code="possible_duplicate",
            status="open",
        )
        session.add_all([source, issue])
        session.commit()
    engine.dispose()

    client = TestClient(app)
    login_res = client.post(
        "/admin/login",
        json={"email": "admin@carvalue.ca", "password": "SuperSecretAdmin123!"},
    )
    csrf_token = login_res.json()["csrf_token"]

    # 1. Toggle source
    toggle_res = client.post("/admin/sources/10/toggle", headers={"x-csrf-token": csrf_token})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    # 2. Resolve data quality issue
    resolve_res = client.post(
        "/admin/data-quality/20/resolve",
        json={"action": "resolved", "notes": "Verified unique vehicle identity"},
        headers={"x-csrf-token": csrf_token},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"
