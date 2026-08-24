"""M3 test suite: offline valuation proof, OLS baseline, CatBoost candidate,
and metrics (FR-ML-01 to FR-ML-10).
"""

from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from carvalue_core.confidence import ConfidenceLabel
from carvalue_core.models import (
    CatBoostCandidate,
    OLSBaseline,
    ValuationModel,
    chronological_split,
    compute_metrics,
    evaluate_prediction,
)
from carvalue_core.reasons import ReasonCode


@pytest.fixture
def ford_ranger_df() -> pd.DataFrame:
    """Representative Ford Ranger training dataset."""
    dates = [
        datetime(2026, 1, 15, tzinfo=UTC),
        datetime(2026, 2, 1, tzinfo=UTC),
        datetime(2026, 3, 10, tzinfo=UTC),
        datetime(2026, 4, 5, tzinfo=UTC),
        datetime(2026, 5, 20, tzinfo=UTC),
        datetime(2026, 6, 12, tzinfo=UTC),
        datetime(2026, 7, 18, tzinfo=UTC),
        datetime(2026, 8, 1, tzinfo=UTC),
    ]
    data = {
        "model_year": [2019, 2020, 2021, 2021, 2022, 2022, 2023, 2023],
        "mileage_km": [95000, 78000, 60000, 52000, 38000, 31000, 18000, 12000],
        "price_cad": [23500.0, 26000.0, 28500.0, 29800.0, 32500.0, 33900.0, 37000.0, 38500.0],
        "trim": ["xl", "xlt", "xlt", "lariat", "xlt", "lariat", "xlt", "lariat"],
        "drivetrain": ["2wd", "4wd", "4wd", "4wd", "4wd", "4wd", "4wd", "4wd"],
        "seller_type": [
            "private",
            "dealer",
            "private",
            "dealer",
            "dealer",
            "dealer",
            "dealer",
            "dealer",
        ],
        "observed_at": dates,
    }
    return pd.DataFrame(data)


def test_chronological_split_preserves_temporal_order(ford_ranger_df: pd.DataFrame) -> None:
    train_df, val_df, test_df = chronological_split(
        ford_ranger_df, time_column="observed_at", train_ratio=0.5, val_ratio=0.25
    )

    assert len(train_df) + len(val_df) + len(test_df) == len(ford_ranger_df)
    assert train_df["observed_at"].max() <= val_df["observed_at"].min()
    assert val_df["observed_at"].max() <= test_df["observed_at"].min()


def test_ols_baseline_fitting_and_prediction(ford_ranger_df: pd.DataFrame) -> None:
    model = OLSBaseline()
    ref_date = date(2026, 8, 20)
    model.fit(ford_ranger_df, reference_date=ref_date)

    assert model.is_fitted
    assert model.params is not None
    assert len(model.params) == 3

    features = {
        "model_year": 2022,
        "mileage_km": 35000,
        "valuation_date": ref_date,
    }
    point, low, high = model.predict(features)

    assert 25000.0 < point < 40000.0
    assert low < point < high
    assert high - low > 0


def test_catboost_candidate_fitting_and_intervals(ford_ranger_df: pd.DataFrame) -> None:
    train_df, val_df, _ = chronological_split(ford_ranger_df, train_ratio=0.75, val_ratio=0.25)
    model = CatBoostCandidate()
    ref_date = date(2026, 8, 20)
    model.fit(train_df, df_val=val_df, reference_date=ref_date)

    assert model.is_fitted
    features = {
        "model_year": 2022,
        "mileage_km": 35000,
        "trim": "xlt",
        "drivetrain": "4wd",
        "seller_type": "dealer",
        "valuation_date": ref_date,
    }
    point, low, high = model.predict(features)

    assert point > 0
    assert low <= point <= high


def test_metrics_computation(ford_ranger_df: pd.DataFrame) -> None:
    y_true = np.array([30000.0, 35000.0, 28000.0])
    y_pred = np.array([31000.0, 34000.0, 27500.0])
    y_low = np.array([27000.0, 31000.0, 24000.0])
    y_high = np.array([34000.0, 38000.0, 31000.0])

    metrics = compute_metrics(y_true, y_pred, y_low, y_high, df_eval=ford_ranger_df.iloc[:3])
    m_dict = metrics.to_dict()

    assert m_dict["sample_count"] == 3
    assert m_dict["mae_cad"] > 0
    assert m_dict["mdape"] > 0
    assert m_dict["interval_coverage_80"] == 1.0  # all 3 fell within [y_low, y_high]


def test_model_artifact_save_and_load(tmp_path: Path, ford_ranger_df: pd.DataFrame) -> None:
    model = OLSBaseline()
    model.fit(ford_ranger_df)

    artifact_file = tmp_path / "ols_model.joblib"
    checksum = model.save(artifact_file)

    assert artifact_file.exists()
    assert len(checksum) == 64  # SHA256 length

    loaded = ValuationModel.load(artifact_file)
    assert isinstance(loaded, OLSBaseline)
    assert loaded.is_fitted

    point_orig, _, _ = model.predict({"model_year": 2022, "mileage_km": 40000})
    point_loaded, _, _ = loaded.predict({"model_year": 2022, "mileage_km": 40000})
    assert point_orig == point_loaded


def test_evaluate_prediction_refusal_rules(ford_ranger_df: pd.DataFrame) -> None:
    model = OLSBaseline()
    model.fit(ford_ranger_df)

    # 1. Normal in-distribution prediction with ample comparables -> High/Medium
    decision_normal = evaluate_prediction(
        point_cad=32000.0,
        low_cad=29000.0,
        high_cad=35000.0,
        features={"model_year": 2021, "mileage_km": 50000},
        model=model,
        comparables_count=60,
        data_freshness_days=10.0,
    )
    assert decision_normal.label == ConfidenceLabel.HIGH

    # 2. Sparse segment (< 4 comparables) -> Insufficient Data (FR-PUB-04, FR-ML-10)
    decision_sparse = evaluate_prediction(
        point_cad=32000.0,
        low_cad=29000.0,
        high_cad=35000.0,
        features={"model_year": 2021, "mileage_km": 50000},
        model=model,
        comparables_count=2,
        data_freshness_days=10.0,
    )
    assert decision_sparse.label == ConfidenceLabel.INSUFFICIENT_DATA
    assert ReasonCode.SPARSE_SEGMENT in decision_sparse.notes

    # 3. Hard Out-of-Distribution year (e.g. 1995 when bounds are 2019-2023) -> Insufficient Data
    decision_ood = evaluate_prediction(
        point_cad=32000.0,
        low_cad=29000.0,
        high_cad=35000.0,
        features={"model_year": 1995, "mileage_km": 50000},
        model=model,
        comparables_count=50,
        data_freshness_days=10.0,
    )
    assert decision_ood.label == ConfidenceLabel.INSUFFICIENT_DATA
    assert ReasonCode.OUT_OF_TRAINING_DOMAIN in decision_ood.notes
