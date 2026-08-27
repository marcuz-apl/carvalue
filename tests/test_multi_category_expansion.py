"""Unit and integration tests for Milestone M9: Full Alberta Multi-Category Expansion."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from carvalue_api import app
from carvalue_api.cli import do_init_db
from carvalue_core.models import (
    ModelMetrics,
    SegmentRegressionGate,
)
from carvalue_core.persistence import (
    Listing,
    ListingPriceHistory,
    ModelVersion,
    Source,
    make_engine,
    new_session_factory,
)
from carvalue_core.taxonomy import (
    PickupTaxonomy,
    seed_full_alberta_taxonomy,
)


def test_suv_crossover_taxonomy_resolution() -> None:
    """Verify resolution of SUV and Crossover families, aliases, and categories."""
    tax = PickupTaxonomy.from_nodes(seed_full_alberta_taxonomy())

    # Ford SUVs
    assert tax.resolve_make("Ford") == "ford"
    assert tax.resolve_model("ford", "Escape") == "escape"
    assert tax.resolve_model("ford", "Explorer") == "explorer"
    assert tax.resolve_category("ford", "escape") == "suv"
    assert tax.resolve_category("ford", "explorer") == "suv"
    assert tax.resolve_trim("escape", "Titanium") == "titanium"
    assert tax.resolve_trim("explorer", "ST") == "st"

    # Toyota SUVs
    assert tax.resolve_make("Toyota") == "toyota"
    assert tax.resolve_model("toyota", "RAV4") == "rav4"
    assert tax.resolve_model("toyota", "Highlander") == "highlander"
    assert tax.resolve_category("toyota", "rav4") == "suv"
    assert tax.resolve_trim("rav4", "XLE") == "xle"
    assert tax.resolve_trim("rav4", "Adventure") == "trail"

    # Honda SUVs
    assert tax.resolve_make("Honda") == "honda"
    assert tax.resolve_model("honda", "CR-V") == "cr-v"
    assert tax.resolve_model("honda", "CRV") == "cr-v"
    assert tax.resolve_category("honda", "cr-v") == "suv"
    assert tax.resolve_trim("cr-v", "Touring") == "touring"

    # Jeep SUVs
    assert tax.resolve_make("Jeep") == "jeep"
    assert tax.resolve_model("jeep", "Grand Cherokee") == "grand cherokee"
    assert tax.resolve_category("jeep", "grand cherokee") == "suv"
    assert tax.resolve_trim("grand cherokee", "Trailhawk") == "trailhawk"


def test_sedan_taxonomy_resolution() -> None:
    """Verify resolution of Sedan families, aliases, and categories."""
    tax = PickupTaxonomy.from_nodes(seed_full_alberta_taxonomy())

    # Honda Sedans
    assert tax.resolve_model("honda", "Civic") == "civic"
    assert tax.resolve_model("honda", "Accord") == "accord"
    assert tax.resolve_category("honda", "civic") == "sedan"
    assert tax.resolve_trim("civic", "Touring") == "touring"
    assert tax.resolve_trim("civic", "Si") == "si"

    # Toyota Sedans
    assert tax.resolve_model("toyota", "Camry") == "camry"
    assert tax.resolve_model("toyota", "Corolla") == "corolla"
    assert tax.resolve_category("toyota", "camry") == "sedan"

    # Hyundai Sedans
    assert tax.resolve_make("Hyundai") == "hyundai"
    assert tax.resolve_model("hyundai", "Elantra") == "elantra"
    assert tax.resolve_model("hyundai", "Sonata") == "sonata"
    assert tax.resolve_category("hyundai", "elantra") == "sedan"

    # BMW & Audi Sedans
    assert tax.resolve_make("BMW") == "bmw"
    assert tax.resolve_model("bmw", "330i") == "3 series"
    assert tax.resolve_category("bmw", "3 series") == "sedan"
    assert tax.resolve_model("audi", "A4") == "a4"
    assert tax.resolve_category("audi", "a4") == "sedan"


def test_coupe_van_hatchback_taxonomy_resolution() -> None:
    """Verify Coupes, Vans, and Hatchbacks category mappings and alias resolution."""
    tax = PickupTaxonomy.from_nodes(seed_full_alberta_taxonomy())

    # Coupes
    assert tax.resolve_model("ford", "Mustang") == "mustang"
    assert tax.resolve_category("ford", "mustang") == "coupe"
    assert tax.resolve_trim("mustang", "GT") == "gt"
    assert tax.resolve_model("chevrolet", "Camaro") == "camaro"
    assert tax.resolve_category("chevrolet", "camaro") == "coupe"
    assert tax.resolve_model("dodge", "Challenger") == "challenger"
    assert tax.resolve_category("dodge", "challenger") == "coupe"

    # Vans
    assert tax.resolve_make("Dodge") == "dodge"
    assert tax.resolve_model("dodge", "Grand Caravan") == "grand caravan"
    assert tax.resolve_model("dodge", "Caravan") == "grand caravan"
    assert tax.resolve_category("dodge", "grand caravan") == "van"
    assert tax.resolve_model("chrysler", "Pacifica") == "pacifica"
    assert tax.resolve_category("chrysler", "pacifica") == "van"
    assert tax.resolve_model("toyota", "Sienna") == "sienna"
    assert tax.resolve_category("toyota", "sienna") == "van"

    # Hatchbacks
    assert tax.resolve_make("VW") == "volkswagen"
    assert tax.resolve_model("volkswagen", "Golf GTI") == "golf"
    assert tax.resolve_model("volkswagen", "GTI") == "golf"
    assert tax.resolve_category("volkswagen", "golf") == "hatchback"
    assert tax.resolve_model("mazda", "Mazda 3") == "mazda3"
    assert tax.resolve_category("mazda", "mazda3") == "hatchback"


def test_known_models_by_category_filtering() -> None:
    """Verify querying models filtered by category."""
    tax = PickupTaxonomy.from_nodes(seed_full_alberta_taxonomy())

    suv_models = tax.known_models_by_category("suv")
    assert "ford" in suv_models
    assert "escape" in suv_models["ford"]
    assert "explorer" in suv_models["ford"]
    assert "ranger" not in suv_models["ford"]  # pickup, not SUV

    sedan_models = tax.known_models_by_category("sedan")
    assert "honda" in sedan_models
    assert "civic" in sedan_models["honda"]
    assert "cr-v" not in sedan_models["honda"]  # SUV, not sedan

    pickup_models = tax.known_models_by_category("pickup")
    assert "ford" in pickup_models
    assert "f-150" in pickup_models["ford"]
    assert "escape" not in pickup_models["ford"]


def test_api_taxonomy_endpoint_multi_category(tmp_path: Path) -> None:
    """Verify /v1/taxonomy returns multi-category taxonomy hierarchy."""
    db_path = tmp_path / "multi_cat_tax.db"
    db_url = f"sqlite:///{db_path}"
    app.state.db_url = db_url
    do_init_db(db_url=db_url)

    client = TestClient(app)
    res = client.get("/v1/taxonomy")
    assert res.status_code == 200
    data = res.json()

    assert "makes" in data
    assert "ford" in [m.lower() for m in data["makes"]]
    assert "toyota" in [m.lower() for m in data["makes"]]
    assert "honda" in [m.lower() for m in data["makes"]]

    assert "categories" in data
    assert "suv" in data["categories"]
    assert "sedan" in data["categories"]
    assert "pickup" in data["categories"]

    assert "models_by_category" in data
    assert "models_by_make" in data


def test_multi_category_slice_regression_gate() -> None:
    """Verify SegmentRegressionGate supports category slices (e.g. category:suv, category:sedan)."""
    baseline = ModelMetrics(
        mae_cad=1500.0,
        mdape=0.045,
        rmse_cad=1800.0,
        sample_count=500,
        interval_coverage_80=0.81,
        mean_interval_rel_width=0.20,
        segment_slices={
            "category:pickup": {"mae_cad": 1400.0, "sample_count": 200},
            "category:suv": {"mae_cad": 1550.0, "sample_count": 200},
            "category:sedan": {"mae_cad": 1300.0, "sample_count": 100},
        },
    )

    # Candidate with slight global improvement and all category slices improved
    candidate_pass = ModelMetrics(
        mae_cad=1420.0,
        mdape=0.041,
        rmse_cad=1720.0,
        sample_count=500,
        interval_coverage_80=0.82,
        mean_interval_rel_width=0.19,
        segment_slices={
            "category:pickup": {"mae_cad": 1350.0, "sample_count": 200},
            "category:suv": {"mae_cad": 1480.0, "sample_count": 200},
            "category:sedan": {"mae_cad": 1250.0, "sample_count": 100},
        },
    )

    eval_pass = SegmentRegressionGate.evaluate(baseline, candidate_pass)
    assert eval_pass.passed is True
    assert len(eval_pass.regressed_segments) == 0

    # Candidate with SUV category slice regressed by >8%
    candidate_fail = ModelMetrics(
        mae_cad=1450.0,
        mdape=0.043,
        rmse_cad=1750.0,
        sample_count=500,
        interval_coverage_80=0.81,
        mean_interval_rel_width=0.20,
        segment_slices={
            "category:pickup": {"mae_cad": 1300.0, "sample_count": 200},
            "category:suv": {"mae_cad": 1720.0, "sample_count": 200},  # +11.0% regression!
            "category:sedan": {"mae_cad": 1240.0, "sample_count": 100},
        },
    )

    eval_fail = SegmentRegressionGate.evaluate(
        baseline, candidate_fail, max_allowed_slice_mae_degradation_pct=0.08
    )
    assert eval_fail.passed is False
    assert any("category:suv" in seg for seg in eval_fail.regressed_segments)
