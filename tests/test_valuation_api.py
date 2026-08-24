"""M4 test suite: Valuation API contract, validation, active-model loading,
refusal rules, and telemetry (FR-PUB-01 to FR-PUB-06, FR-OBS-01).
"""

import time
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest
from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_core.confidence import ConfidenceLabel
from carvalue_core.models import OLSBaseline
from carvalue_core.persistence import (
    Listing,
    ListingPriceHistory,
    ModelVersion,
    Source,
    ValuationEvent,
    make_engine,
    new_session_factory,
)
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def api_test_db(tmp_path: Path) -> str:
    """Initialize a fresh SQLite database with migrations and taxonomy."""
    db_path = tmp_path / "api_test.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)
    return db_url


@pytest.fixture
def active_model(api_test_db: str, tmp_path: Path) -> ModelVersion:
    """Train and persist an active OLS baseline model in the test database."""
    # Create sample training data
    dates = [
        datetime(2026, 1, 15, tzinfo=UTC),
        datetime(2026, 3, 10, tzinfo=UTC),
        datetime(2026, 5, 20, tzinfo=UTC),
        datetime(2026, 7, 18, tzinfo=UTC),
    ]
    df = pd.DataFrame(
        {
            "model_year": [2019, 2021, 2022, 2023],
            "mileage_km": [90000, 55000, 35000, 15000],
            "price_cad": [24000.0, 29000.0, 33000.0, 38000.0],
            "trim": ["xl", "xlt", "xlt", "lariat"],
            "drivetrain": ["2wd", "4wd", "4wd", "4wd"],
            "seller_type": ["private", "dealer", "dealer", "dealer"],
            "observed_at": dates,
        }
    )
    model = OLSBaseline()
    model.fit(df, reference_date=date(2026, 8, 20))

    artifact_path = tmp_path / "active_model.joblib"
    checksum = model.save(artifact_path)

    engine = make_engine(api_test_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        model_ver = ModelVersion(
            algorithm="ols_baseline",
            status="active",
            artifact_path=str(artifact_path),
            feature_schema_json=model.feature_schema,
            metrics_json={"mae_cad": 500.0, "mdape": 0.02, "sample_count": 4},
            trained_at_utc=datetime.now(UTC),
            model_hash_sha256=checksum,
        )
        session.add(model_ver)
        session.commit()
        session.refresh(model_ver)

    engine.dispose()
    return model_ver


def seed_comparables(db_url: str, count: int = 50) -> None:
    """Seed active listing comparables in the test database."""
    engine = make_engine(db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        source = session.get(Source, 1)
        if source is None:
            source = Source(
                id=1,
                name="test_seed_feed",
                source_type="api_feed",
                permission_status="approved",
                enabled=True,
            )
            session.add(source)
            session.flush()

        for i in range(count):
            listing = Listing(
                source_id=1,
                source_record_id=f"test-ranger-{i}",
                fingerprint_sha256=f"hash-{i:04d}",
                make="ford",
                model="ranger",
                trim="xlt",
                drivetrain="4wd",
                seller_type="dealer",
                model_year=2022,
                mileage_km=35000 + i * 100,
                asking_price_cad_cents=3300000 + i * 1000,
                price_observed_at=datetime(2026, 8, 15, tzinfo=UTC),
                first_seen_at=datetime(2026, 8, 1, tzinfo=UTC),
                last_seen_at=datetime(2026, 8, 15, tzinfo=UTC),
                is_active=True,
            )
            session.add(listing)
            session.flush()

            price_hist = ListingPriceHistory(
                listing_id=listing.id,
                observed_at=datetime(2026, 8, 15, tzinfo=UTC),
                asking_price_cad_cents=3300000 + i * 1000,
            )
            session.add(price_hist)
        session.commit()
    engine.dispose()


def test_healthz_endpoint(api_test_db: str) -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_taxonomy_endpoint(api_test_db: str) -> None:
    client = TestClient(app)
    response = client.get("/v1/taxonomy")
    assert response.status_code == 200
    data = response.json()
    assert "ford" in data["makes"]
    assert "ranger" in data["models_by_make"].get("ford", [])
    assert "ford:ranger" in data["trims_by_model"]


def test_valuation_happy_path(api_test_db: str, active_model: ModelVersion) -> None:
    """Scenario 1: Supported Alberta vehicle returns rounded CAD estimate and interval."""
    seed_comparables(api_test_db, count=50)

    client = TestClient(app)
    payload = {
        "make": "Ford",
        "model": "Ranger",
        "year": 2022,
        "mileage_km": 35000,
        "trim": "XLT",
        "drivetrain": "4wd",
        "seller_type": "dealer",
    }
    headers = {
        "x-valuation-date": "2026-08-20",
        "x-visitor-id": "visitor-test-123",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    start = time.perf_counter()
    response = client.post("/v1/valuations", json=payload, headers=headers)
    duration = time.perf_counter() - start

    assert response.status_code == 200
    data = response.json()

    assert data["estimate_cad"] % 100 == 0  # Rounded to nearest $100 CAD
    assert 25000 <= data["estimate_cad"] <= 40000
    assert data["interval_low_cad"] <= data["estimate_cad"] <= data["interval_high_cad"]
    assert data["confidence_label"] == ConfidenceLabel.HIGH
    assert data["comparables_count"] == 50
    assert data["data_freshness_days"] == 5.0  # Aug 20 - Aug 15 = 5 days
    assert data["valuation_date"] == "2026-08-20"
    assert "estimate, not a professional appraisal" in data["disclaimer"]
    assert duration < 3.0  # Fast response time under 3 seconds

    # Verify telemetry was recorded
    engine = make_engine(api_test_db)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        events = session.execute(select(ValuationEvent)).scalars().all()
        assert len(events) == 1
        assert events[0].confidence_label == ConfidenceLabel.HIGH
        assert events[0].visitor_id == "visitor-test-123"
        assert events[0].device_class == "desktop"
    engine.dispose()


def test_unsupported_vehicle_returns_insufficient_data(
    api_test_db: str, active_model: ModelVersion
) -> None:
    """Scenario 2: Unsupported vehicle returns Insufficient Data without fabricated precision."""
    client = TestClient(app)
    payload = {
        "make": "Honda",
        "model": "Civic",
        "year": 2022,
        "mileage_km": 30000,
    }
    response = client.post("/v1/valuations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["confidence_label"] == ConfidenceLabel.INSUFFICIENT_DATA
    assert data["estimate_cad"] == 0
    assert data["interval_low_cad"] == 0
    assert data["interval_high_cad"] == 0


def test_sparse_comparables_returns_insufficient_data(
    api_test_db: str, active_model: ModelVersion
) -> None:
    """Scenario 8: Sparse comparables (< 4) returns Insufficient Data."""
    seed_comparables(api_test_db, count=2)  # only 2 comparables

    client = TestClient(app)
    payload = {
        "make": "Ford",
        "model": "Ranger",
        "year": 2022,
        "mileage_km": 35000,
    }
    response = client.post("/v1/valuations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["confidence_label"] == ConfidenceLabel.INSUFFICIENT_DATA
    assert data["estimate_cad"] == 0
    assert data["comparables_count"] == 2


def test_out_of_distribution_input_returns_insufficient_data(
    api_test_db: str, active_model: ModelVersion
) -> None:
    """Scenario 2 & 8: Out of training domain inputs return Insufficient Data."""
    seed_comparables(api_test_db, count=50)

    client = TestClient(app)
    # Model year 2011 is outside the active model bounds [2019, 2023]
    payload = {
        "make": "Ford",
        "model": "Ranger",
        "year": 2011,
        "mileage_km": 40000,
    }
    response = client.post("/v1/valuations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["confidence_label"] == ConfidenceLabel.INSUFFICIENT_DATA
    assert data["estimate_cad"] == 0


def test_invalid_input_validation(api_test_db: str) -> None:
    """Validation at boundary: Negative mileage or implausible year rejected with 422."""
    client = TestClient(app)
    response = client.post(
        "/v1/valuations",
        json={"make": "Ford", "model": "Ranger", "year": 1980, "mileage_km": -100},
    )
    assert response.status_code == 422
