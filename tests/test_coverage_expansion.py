"""Unit and integration tests for Milestone M8: Coverage expansion and governance."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_core.models import (
    ModelMetrics,
    SegmentRegressionGate,
    SegmentRegressionResult,
)
from carvalue_core.persistence import (
    ValuationEvent,
    make_engine,
    new_session_factory,
)
from carvalue_core.taxonomy import (
    PickupTaxonomy,
    seed_alberta_regions,
    seed_pickup_taxonomy,
)


def test_heavy_duty_taxonomy_resolution() -> None:
    """Verify resolution of heavy-duty pickup families and aliases."""
    tax = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())

    # Ford Super Duty
    assert tax.resolve_make("Ford") == "ford"
    assert tax.resolve_model("ford", "F-250") == "super duty f-250"
    assert tax.resolve_model("ford", "f250") == "super duty f-250"
    assert tax.resolve_model("ford", "Super Duty 350") == "super duty f-350"
    assert tax.resolve_trim("super duty f-250", "King Ranch") == "king ranch"
    assert tax.resolve_trim("super duty f-250", "Lariat") == "lariat"

    # GM Heavy-Duty
    assert tax.resolve_make("Chevy") == "chevrolet"
    assert tax.resolve_model("chevrolet", "Silverado 2500HD") == "silverado 2500hd"
    assert tax.resolve_model("chevrolet", "2500") == "silverado 2500hd"
    assert tax.resolve_trim("silverado", "High Country") == "high country"
    assert tax.resolve_trim("silverado", "Work Truck") == "wt"

    # GMC Heavy-Duty
    assert tax.resolve_make("GMC") == "gmc"
    assert tax.resolve_model("gmc", "Sierra 2500HD") == "sierra 2500hd"
    assert tax.resolve_trim("sierra", "Denali Ultimate") == "denali ultimate"

    # Ram Heavy-Duty
    assert tax.resolve_make("Dodge Ram") == "ram"
    assert tax.resolve_model("ram", "2500") == "2500"
    assert tax.resolve_model("ram", "3500") == "3500"
    assert tax.resolve_trim("1500", "Lone Star") == "big horn"

    # Toyota & Nissan
    assert tax.resolve_model("toyota", "Tundra") == "tundra"
    assert tax.resolve_trim("tacoma", "TRD Off Road") == "trd off-road"
    assert tax.resolve_model("nissan", "Titan") == "titan"


def test_alberta_regions_resolution() -> None:
    """Verify Alberta geographic sub-market resolution."""
    tax = PickupTaxonomy.from_nodes(seed_alberta_regions())

    assert tax.resolve_region("Calgary") == "calgary_region"
    assert tax.resolve_region("Airdrie") == "calgary_region"
    assert tax.resolve_region("Edmonton") == "edmonton_region"
    assert tax.resolve_region("St Albert") == "edmonton_region"
    assert tax.resolve_region("Red Deer") == "red_deer_central"
    assert tax.resolve_region("Lethbridge") == "lethbridge_south"
    assert tax.resolve_region("Medicine Hat") == "medicine_hat_southeast"
    assert tax.resolve_region("Fort McMurray") == "fort_mcmurray_north"
    assert tax.resolve_region("Grande Prairie") == "grande_prairie_peace"
    assert tax.resolve_region("Unknown Location") is None


def test_segment_regression_gate_approval() -> None:
    """Gate passes when candidate metrics improve or stay within allowed threshold."""
    baseline = ModelMetrics(
        mae_cad=1200.0,
        mdape=0.038,
        rmse_cad=1500.0,
        sample_count=100,
        interval_coverage_80=0.81,
        mean_interval_rel_width=0.22,
        segment_slices={
            "make:ford": {"mae_cad": 1150.0, "sample_count": 50},
            "make:chevrolet": {"mae_cad": 1250.0, "sample_count": 50},
        },
    )

    # Candidate has better global MAE and all slices improved
    candidate_improved = ModelMetrics(
        mae_cad=1100.0,
        mdape=0.035,
        rmse_cad=1400.0,
        sample_count=100,
        interval_coverage_80=0.82,
        mean_interval_rel_width=0.21,
        segment_slices={
            "make:ford": {"mae_cad": 1080.0, "sample_count": 50},
            "make:chevrolet": {"mae_cad": 1120.0, "sample_count": 50},
        },
    )

    result = SegmentRegressionGate.evaluate(baseline, candidate_improved)
    assert result.passed is True
    assert len(result.regressed_segments) == 0


def test_segment_regression_gate_blocks_slice_degradation() -> None:
    """PRD FR-ML-08: A global improvement cannot hide a material slice regression (>8%)."""
    baseline = ModelMetrics(
        mae_cad=1200.0,
        mdape=0.038,
        rmse_cad=1500.0,
        sample_count=100,
        interval_coverage_80=0.81,
        mean_interval_rel_width=0.22,
        segment_slices={
            "model:ranger": {"mae_cad": 1000.0, "sample_count": 30},
            "model:f-150": {"mae_cad": 1400.0, "sample_count": 70},
        },
    )

    # Candidate has better global MAE ($1150 vs $1200), but Ranger slice regressed from $1000 to $1120 (+12%)
    candidate_with_regression = ModelMetrics(
        mae_cad=1150.0,
        mdape=0.036,
        rmse_cad=1450.0,
        sample_count=100,
        interval_coverage_80=0.82,
        mean_interval_rel_width=0.21,
        segment_slices={
            "model:ranger": {"mae_cad": 1120.0, "sample_count": 30},  # +12% regression!
            "model:f-150": {"mae_cad": 1160.0, "sample_count": 70},   # improved
        },
    )

    result = SegmentRegressionGate.evaluate(
        baseline, candidate_with_regression, max_allowed_slice_mae_degradation_pct=0.08
    )
    assert result.passed is False
    assert len(result.regressed_segments) == 1
    assert "model:ranger" in result.regressed_segments[0]
    assert "+12.0%" in result.regressed_segments[0]


def test_visitor_feedback_submission(tmp_path: Path) -> None:
    """Verify POST /v1/valuations/feedback records visitor rating anonymously."""
    db_path = tmp_path / "feedback_test.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)

    engine = make_engine(db_url)
    SessionLocal = new_session_factory(engine)
    with SessionLocal() as session:
        event = ValuationEvent(
            id=42,
            occurred_at=datetime.now(UTC),
            event_type="valuation",
            confidence_label="high",
            comparables_count=12,
            interval_level=80,
            latency_ms=45,
            device_class="mobile",
        )
        session.add(event)
        session.commit()
    engine.dispose()

    client = TestClient(app)

    # 1. Submit feedback on existing valuation event
    fb_res = client.post(
        "/v1/valuations/feedback",
        json={"valuation_event_id": 42, "feedback_useful": True},
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["ok"] is True
    assert fb_res.json()["feedback_useful"] is True

    # Check database
    with SessionLocal() as session:
        ev = session.get(ValuationEvent, 42)
        assert ev is not None
        assert ev.feedback_useful is True
    engine.dispose()

    # 2. Submit anonymous standalone feedback with notes
    gen_res = client.post(
        "/v1/valuations/feedback",
        json={"feedback_useful": False, "feedback_notes": "Estimated price was higher than local dealer inventory"},
    )
    assert gen_res.status_code == 200
    assert gen_res.json()["ok"] is True
