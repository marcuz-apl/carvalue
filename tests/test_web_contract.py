"""End-to-end contract and structure tests for M6 Public Web Experience."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_core.persistence import (
    Listing,
    ListingPriceHistory,
    ModelVersion,
    Source,
    make_engine,
    new_session_factory,
)
from carvalue_core.models import OLSBaseline
from datetime import UTC, datetime, date


@pytest.fixture
def web_e2e_db(tmp_path: Path) -> str:
    db_path = tmp_path / "web_e2e_test.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)

    # Train and save baseline model
    import pandas as pd

    df = pd.DataFrame(
        [
            {"model_year": 2022, "mileage_km": 30000, "price_cad": 32000.0},
            {"model_year": 2022, "mileage_km": 40000, "price_cad": 30000.0},
            {"model_year": 2021, "mileage_km": 50000, "price_cad": 28000.0},
            {"model_year": 2021, "mileage_km": 60000, "price_cad": 26000.0},
            {"model_year": 2020, "mileage_km": 70000, "price_cad": 24000.0},
        ]
    )
    model = OLSBaseline()
    model.fit(df, reference_date=date(2026, 8, 20))
    artifact_file = tmp_path / "ols_model.joblib"
    model.save(str(artifact_file))

    engine = make_engine(db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        # Seed Source
        source = Source(
            id=1,
            name="test_source",
            source_type="api_feed",
            permission_status="approved",
            enabled=True,
        )
        session.add(source)
        session.flush()

        # Seed Active ModelVersion
        m = ModelVersion(
            algorithm="ols_baseline",
            status="active",
            artifact_path=str(artifact_file),
            feature_schema_json={"features": ["model_year", "mileage_km"]},
            metrics_json={"mae_cad": 1200.0},
            trained_at_utc=datetime.now(UTC),
            model_hash_sha256="test_hash_sha256",
        )
        session.add(m)
        session.flush()

        # Seed 5 Active Comparables for Ford Ranger
        for i in range(5):
            listing = Listing(
                id=100 + i,
                source_id=1,
                source_record_id=f"rec-{i}",
                fingerprint_sha256=f"fp-{i}",
                make="ford",
                model="ranger",
                trim="xlt",
                model_year=2022,
                mileage_km=40000 + i * 1000,
                asking_price_cad_cents=3100000,
                price_observed_at=datetime(2026, 8, 15, tzinfo=UTC),
                is_active=True,
                first_seen_at=datetime(2026, 8, 15, tzinfo=UTC),
                last_seen_at=datetime(2026, 8, 15, tzinfo=UTC),
            )
            session.add(listing)
            price_hist = ListingPriceHistory(
                listing_id=100 + i,
                asking_price_cad_cents=3100000,
                observed_at=datetime(2026, 8, 15, tzinfo=UTC),
            )
            session.add(price_hist)

        session.commit()
    engine.dispose()
    return db_url


def test_web_app_file_structure() -> None:
    """Verify all Next.js M6 pages, components, types, and styles exist."""
    base = Path("/mnt/e/projects/CarValue/apps/web")
    required_files = [
        base / "package.json",
        base / "tsconfig.json",
        base / "next.config.js",
        base / "src/app/globals.css",
        base / "src/app/layout.tsx",
        base / "src/app/page.tsx",
        base / "src/app/privacy/page.tsx",
        base / "src/app/methodology/page.tsx",
        base / "src/components/ValuationForm.tsx",
        base / "src/components/ValuationResult.tsx",
        base / "src/components/RefusalCard.tsx",
        base / "src/components/AdminPanel.tsx",
        base / "src/lib/types.ts",
        base / "src/lib/api.ts",
    ]
    for rf in required_files:
        assert rf.exists(), f"Missing required file: {rf}"


def test_visitor_happy_path_e2e_contract(web_e2e_db: str) -> None:
    """PRD Scenario: Visitor requests 2022 Ford Ranger XLT 4WD with 45,000 km."""
    client = TestClient(app)
    payload = {
        "make": "Ford",
        "model": "Ranger",
        "year": 2022,
        "mileage_km": 45000,
        "trim": "XLT",
        "drivetrain": "4wd",
        "seller_type": "dealer",
    }
    response = client.post("/v1/valuations", json=payload, headers={"x-valuation-date": "2026-08-20"})
    assert response.status_code == 200
    data = response.json()

    # 1. Asking price estimate rounded to nearest $100 CAD
    assert data["estimate_cad"] > 0
    assert data["estimate_cad"] % 100 == 0

    # 2. 80% Prediction interval
    assert data["interval_low_cad"] <= data["estimate_cad"] <= data["interval_high_cad"]

    # 3. Evidence & confidence label
    assert data["confidence_label"] in ("high", "medium", "low")
    assert data["comparables_count"] >= 4
    assert data["data_freshness_days"] >= 0

    # 4. Mandatory disclaimer
    assert "estimate" in data["disclaimer"].lower()


def test_visitor_sparse_comparables_triggers_refusal(web_e2e_db: str) -> None:
    """PRD Scenario: Sparse segment (<4 comparables) refuses point estimate without guessing."""
    client = TestClient(app)
    # Toyota Tacoma has 0 comparables seeded
    payload = {
        "make": "Toyota",
        "model": "Tacoma",
        "year": 2022,
        "mileage_km": 30000,
        "trim": "TRD Sport",
        "drivetrain": "4wd",
        "seller_type": "dealer",
    }
    response = client.post("/v1/valuations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["confidence_label"] == "insufficient_data"
    assert data["estimate_cad"] == 0
    assert data["interval_low_cad"] == 0
    assert data["interval_high_cad"] == 0


def test_zero_auth_or_tracking_required(web_e2e_db: str) -> None:
    """PRD Section 10: Zero visitor identity or cookies required for public valuations."""
    client = TestClient(app)
    payload = {
        "make": "Ford",
        "model": "Ranger",
        "year": 2022,
        "mileage_km": 45000,
    }
    # No Authorization header, no session cookies
    response = client.post("/v1/valuations", json=payload)
    assert response.status_code == 200
    assert response.json()["estimate_cad"] > 0
