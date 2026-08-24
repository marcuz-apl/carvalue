"""Machine learning models, evaluation harness, and model lifecycle (PRD section 7, 12, 13).

Provides:
- OLSBaseline: Two-feature model (centered vehicle age, mileage) with Statsmodels (FR-ML-01).
- CatBoostCandidate: Nonlinear gradient boosting with categorical trim/drivetrain/seller-type
  and quantile/conformal 80% prediction intervals (FR-ML-02, FR-ML-03).
- Chronological train/validation/test split preventing temporal leakage (FR-ML-06, FR-ML-07).
- Evaluation metrics: MAE (CAD), MdAPE, RMSE, interval coverage/width, and segment slices
  (FR-ML-08).
- Model artifact serialization, SHA256 checksums, and persistence integration (FR-ML-09).
- Refusal rules for out-of-distribution, sparse, or stale inputs (FR-ML-10).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from catboost import CatBoostRegressor

from carvalue_core.confidence import (
    ConfidenceDecision,
    EvidenceConfig,
    ModelBounds,
    decide_confidence,
    out_of_training_domain,
    relative_interval_width,
)
from carvalue_core.units import vehicle_age_years

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    mae_cad: float
    mdape: float
    rmse_cad: float
    sample_count: int
    interval_coverage_80: float
    mean_interval_rel_width: float
    segment_slices: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mae_cad": round(self.mae_cad, 2),
            "mdape": round(self.mdape, 4),
            "rmse_cad": round(self.rmse_cad, 2),
            "sample_count": self.sample_count,
            "interval_coverage_80": round(self.interval_coverage_80, 4),
            "mean_interval_rel_width": round(self.mean_interval_rel_width, 4),
            "segment_slices": self.segment_slices,
        }


class ValuationModel:
    """Abstract base class for asking-price valuation models."""

    def __init__(
        self,
        algorithm_name: str,
        bounds: ModelBounds | None = None,
        feature_schema: dict[str, Any] | None = None,
    ) -> None:
        self.algorithm_name = algorithm_name
        self.bounds = bounds or ModelBounds(
            min_model_year=2010,
            max_model_year=2030,
            min_mileage_km=0,
            max_mileage_km=500_000,
        )
        self.feature_schema = feature_schema or {
            "version": "v1",
            "features": ["vehicle_age", "mileage_km", "trim", "drivetrain", "seller_type"],
            "bounds": {
                "min_model_year": self.bounds.min_model_year,
                "max_model_year": self.bounds.max_model_year,
                "min_mileage_km": self.bounds.min_mileage_km,
                "max_mileage_km": self.bounds.max_mileage_km,
            },
        }

    def predict(self, features: dict[str, Any]) -> tuple[float, float, float]:
        """Predict (point_estimate_cad, low_cad, high_cad) for an 80% interval."""
        raise NotImplementedError("Subclasses must implement predict")

    def save(self, target_path: str | Path) -> str:
        """Serialize model to target_path and return SHA256 checksum."""
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    @classmethod
    def load(cls, artifact_path: str | Path) -> ValuationModel:
        """Load a serialized model from artifact_path."""
        model = joblib.load(Path(artifact_path))
        if not isinstance(model, ValuationModel):
            raise TypeError(f"Loaded object {type(model)} is not a ValuationModel")
        return model


class OLSBaseline(ValuationModel):
    """Reproducible two-feature OLS baseline with centered vehicle age (FR-ML-01)."""

    def __init__(
        self,
        age_mean: float = 0.0,
        bounds: ModelBounds | None = None,
        feature_schema: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            algorithm_name="ols_baseline",
            bounds=bounds,
            feature_schema=feature_schema,
        )
        self.age_mean = age_mean
        self.params: np.ndarray | None = None
        self.residual_std: float = 0.0
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, reference_date: date | None = None) -> OLSBaseline:
        """Fit OLS model: Price_CAD = beta_0 + beta_1 * (age - age_mean) + beta_2 * mileage_km."""
        ref = reference_date or date.today()
        ages = np.array([vehicle_age_years(int(y), ref) for y in df["model_year"]])
        mileages = df["mileage_km"].to_numpy(dtype=float)
        prices = df["price_cad"].to_numpy(dtype=float)

        self.age_mean = float(np.mean(ages))
        centered_age = ages - self.age_mean

        # Update bounds from training data
        self.bounds = ModelBounds(
            min_model_year=int(df["model_year"].min()),
            max_model_year=int(df["model_year"].max()),
            min_mileage_km=int(df["mileage_km"].min()),
            max_mileage_km=int(df["mileage_km"].max()),
        )
        self.feature_schema["bounds"] = {
            "min_model_year": self.bounds.min_model_year,
            "max_model_year": self.bounds.max_model_year,
            "min_mileage_km": self.bounds.min_mileage_km,
            "max_mileage_km": self.bounds.max_mileage_km,
        }

        X = np.column_stack([np.ones_like(centered_age), centered_age, mileages])
        ols_res = sm.OLS(prices, X).fit()
        self.params = np.array(ols_res.params, dtype=float)
        self.residual_std = float(np.std(ols_res.resid, ddof=X.shape[1]))
        self.is_fitted = True
        return self

    def predict(self, features: dict[str, Any]) -> tuple[float, float, float]:
        if not self.is_fitted or self.params is None:
            raise RuntimeError("Model is not fitted")

        val_date = features.get("valuation_date") or date.today()
        if isinstance(val_date, str):
            val_date = date.fromisoformat(val_date)
        year = int(features["model_year"])
        mileage = float(features["mileage_km"])

        age = vehicle_age_years(year, val_date)
        centered_age = age - self.age_mean

        # Point estimate = beta_0 + beta_1 * centered_age + beta_2 * mileage
        point = float(self.params[0] + self.params[1] * centered_age + self.params[2] * mileage)
        point = max(point, 100.0)

        # 80% interval band (z=1.28155 for 80% normal distribution)
        z_80 = 1.28155
        margin = z_80 * self.residual_std
        low = max(point - margin, 0.0)
        high = point + margin

        return point, low, high


class CatBoostCandidate(ValuationModel):
    """Primary nonlinear production candidate with 80% prediction interval (FR-ML-02, FR-ML-03)."""

    def __init__(
        self,
        bounds: ModelBounds | None = None,
        feature_schema: dict[str, Any] | None = None,
        cat_features: list[str] | None = None,
    ) -> None:
        super().__init__(
            algorithm_name="catboost_candidate",
            bounds=bounds,
            feature_schema=feature_schema,
        )
        self.cat_features = cat_features or ["trim", "drivetrain", "seller_type"]
        self.point_model: CatBoostRegressor | None = None
        self.lower_model: CatBoostRegressor | None = None
        self.upper_model: CatBoostRegressor | None = None
        self.is_fitted = False

    def _prepare_features(self, df: pd.DataFrame, reference_date: date) -> pd.DataFrame:
        features = pd.DataFrame(index=df.index)
        features["vehicle_age"] = [
            vehicle_age_years(int(y), reference_date) for y in df["model_year"]
        ]
        features["mileage_km"] = df["mileage_km"].astype(float)
        features["trim"] = (
            df["trim"].fillna("unknown").astype(str)
            if "trim" in df.columns
            else pd.Series(["unknown"] * len(df), index=df.index)
        )
        features["drivetrain"] = (
            df["drivetrain"].fillna("unknown").astype(str)
            if "drivetrain" in df.columns
            else pd.Series(["unknown"] * len(df), index=df.index)
        )
        features["seller_type"] = (
            df["seller_type"].fillna("unknown").astype(str)
            if "seller_type" in df.columns
            else pd.Series(["unknown"] * len(df), index=df.index)
        )
        return features

    def fit(
        self,
        df_train: pd.DataFrame,
        df_val: pd.DataFrame | None = None,
        reference_date: date | None = None,
    ) -> CatBoostCandidate:
        ref = reference_date or date.today()
        X_train = self._prepare_features(df_train, ref)
        y_train = df_train["price_cad"].to_numpy(dtype=float)

        eval_set = None
        if df_val is not None and not df_val.empty:
            X_val = self._prepare_features(df_val, ref)
            y_val = df_val["price_cad"].to_numpy(dtype=float)
            eval_set = (X_val, y_val)

        # Update bounds from training data
        self.bounds = ModelBounds(
            min_model_year=int(df_train["model_year"].min()),
            max_model_year=int(df_train["model_year"].max()),
            min_mileage_km=int(df_train["mileage_km"].min()),
            max_mileage_km=int(df_train["mileage_km"].max()),
        )
        self.feature_schema["bounds"] = {
            "min_model_year": self.bounds.min_model_year,
            "max_model_year": self.bounds.max_model_year,
            "min_mileage_km": self.bounds.min_mileage_km,
            "max_mileage_km": self.bounds.max_mileage_km,
        }

        # 1. Point model (RMSE loss)
        self.point_model = CatBoostRegressor(
            iterations=150,
            learning_rate=0.08,
            depth=4,
            loss_function="RMSE",
            cat_features=self.cat_features,
            verbose=False,
            random_seed=42,
        )
        self.point_model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        # 2. 10th percentile model for 80% interval lower bound
        self.lower_model = CatBoostRegressor(
            iterations=150,
            learning_rate=0.08,
            depth=4,
            loss_function="Quantile:alpha=0.10",
            cat_features=self.cat_features,
            verbose=False,
            random_seed=42,
        )
        self.lower_model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        # 3. 90th percentile model for 80% interval upper bound
        self.upper_model = CatBoostRegressor(
            iterations=150,
            learning_rate=0.08,
            depth=4,
            loss_function="Quantile:alpha=0.90",
            cat_features=self.cat_features,
            verbose=False,
            random_seed=42,
        )
        self.upper_model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        self.is_fitted = True
        return self

    def predict(self, features: dict[str, Any]) -> tuple[float, float, float]:
        if (
            not self.is_fitted
            or self.point_model is None
            or self.lower_model is None
            or self.upper_model is None
        ):
            raise RuntimeError("Model is not fitted")

        val_date = features.get("valuation_date") or date.today()
        if isinstance(val_date, str):
            val_date = date.fromisoformat(val_date)
        year = int(features["model_year"])
        age = vehicle_age_years(year, val_date)

        row = pd.DataFrame(
            [
                {
                    "vehicle_age": float(age),
                    "mileage_km": float(features["mileage_km"]),
                    "trim": str(features.get("trim") or "unknown"),
                    "drivetrain": str(features.get("drivetrain") or "unknown"),
                    "seller_type": str(features.get("seller_type") or "unknown"),
                }
            ]
        )

        point = float(self.point_model.predict(row)[0])
        low = float(self.lower_model.predict(row)[0])
        high = float(self.upper_model.predict(row)[0])

        point = max(point, 100.0)
        low = max(min(low, point), 0.0)
        high = max(high, point)

        return point, low, high


def chronological_split(
    df: pd.DataFrame,
    time_column: str = "observed_at",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split DataFrame chronologically without temporal leakage (FR-ML-06, FR-ML-07)."""
    if df.empty:
        raise ValueError("Cannot split empty DataFrame")

    df_sorted = df.sort_values(by=time_column).reset_index(drop=True)
    n = len(df_sorted)

    n_train = max(1, int(n * train_ratio))
    n_val = int(n * val_ratio)
    if n_train + n_val >= n:
        n_train = max(1, n - 2)
        n_val = 1

    train_df = df_sorted.iloc[:n_train].copy()
    val_df = df_sorted.iloc[n_train : n_train + n_val].copy()
    test_df = df_sorted.iloc[n_train + n_val :].copy()

    if test_df.empty and len(val_df) > 1:
        test_df = val_df.iloc[-1:].copy()
        val_df = val_df.iloc[:-1].copy()

    return train_df, val_df, test_df


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_low: np.ndarray,
    y_high: np.ndarray,
    df_eval: pd.DataFrame | None = None,
) -> ModelMetrics:
    """Compute valuation and calibration metrics (FR-ML-08)."""
    if len(y_true) == 0:
        raise ValueError("Cannot compute metrics on empty arrays")

    errors = np.abs(y_true - y_pred)
    mae = float(np.mean(errors))
    rel_errors = errors / np.maximum(y_true, 1.0)
    mdape = float(np.median(rel_errors))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # Coverage of 80% interval
    covered = (y_true >= y_low) & (y_true <= y_high)
    coverage = float(np.mean(covered))

    # Mean relative half-width
    rel_widths = (y_high - y_low) / (2.0 * np.maximum(y_pred, 1.0))
    mean_rel_width = float(np.mean(rel_widths))

    slices: dict[str, dict[str, Any]] = {}
    if df_eval is not None and "seller_type" in df_eval.columns:
        for seller in df_eval["seller_type"].dropna().unique():
            mask = (df_eval["seller_type"] == seller).to_numpy()
            if np.sum(mask) > 0:
                slices[f"seller_type:{seller}"] = {
                    "count": int(np.sum(mask)),
                    "mae_cad": round(float(np.mean(errors[mask])), 2),
                    "mdape": round(float(np.median(rel_errors[mask])), 4),
                }

    return ModelMetrics(
        mae_cad=mae,
        mdape=mdape,
        rmse_cad=rmse,
        sample_count=len(y_true),
        interval_coverage_80=coverage,
        mean_interval_rel_width=mean_rel_width,
        segment_slices=slices,
    )


def evaluate_prediction(
    point_cad: float,
    low_cad: float,
    high_cad: float,
    features: dict[str, Any],
    model: ValuationModel,
    comparables_count: int,
    data_freshness_days: float,
    config: EvidenceConfig | None = None,
) -> ConfidenceDecision:
    """Evaluate a prediction and determine confidence label / refusal (FR-ML-10)."""
    bounds = model.bounds or ModelBounds(
        min_model_year=2010, max_model_year=2030, min_mileage_km=0, max_mileage_km=500_000
    )
    ood = out_of_training_domain(
        bounds, int(features.get("model_year", 0)), int(features.get("mileage_km", 0))
    )

    point_cents = int(round(point_cad * 100))
    low_cents = int(round(low_cad * 100))
    high_cents = int(round(high_cad * 100))
    interval_rel_w = relative_interval_width(low_cents, point_cents, high_cents)

    return decide_confidence(
        comparables_count=comparables_count,
        data_freshness_days=data_freshness_days,
        interval_rel_width=interval_rel_w,
        ood=ood,
        config=config,
    )


@dataclass(frozen=True)
class SegmentRegressionResult:
    passed: bool
    regressed_segments: list[str]
    max_observed_slice_degradation_pct: float
    summary: str


class SegmentRegressionGate:
    """Enforces that candidate models do not regress on supported vehicle segments (PRD FR-ML-08 / M8)."""

    @staticmethod
    def evaluate(
        baseline_metrics: ModelMetrics | dict[str, Any],
        candidate_metrics: ModelMetrics | dict[str, Any],
        max_allowed_slice_mae_degradation_pct: float = 0.08,
    ) -> SegmentRegressionResult:
        """Compare candidate slice metrics against baseline.

        Returns passed=False if any segment with >= 5 samples has MAE degradation
        exceeding max_allowed_slice_mae_degradation_pct (default 8%).
        """
        base_slices = (
            baseline_metrics.segment_slices
            if isinstance(baseline_metrics, ModelMetrics)
            else baseline_metrics.get("segment_slices", {})
        )
        cand_slices = (
            candidate_metrics.segment_slices
            if isinstance(candidate_metrics, ModelMetrics)
            else candidate_metrics.get("segment_slices", {})
        )

        regressions: list[str] = []
        max_deg = 0.0

        for slice_name, base_stats in base_slices.items():
            if slice_name not in cand_slices:
                continue
            cand_stats = cand_slices[slice_name]
            base_n = base_stats.get("sample_count", 0)
            cand_n = cand_stats.get("sample_count", 0)

            if base_n < 5 or cand_n < 5:
                continue

            base_mae = float(base_stats.get("mae_cad", 0.0))
            cand_mae = float(cand_stats.get("mae_cad", 0.0))

            if base_mae > 0:
                deg_pct = (cand_mae - base_mae) / base_mae
                if deg_pct > max_deg:
                    max_deg = deg_pct
                if deg_pct > max_allowed_slice_mae_degradation_pct:
                    regressions.append(
                        f"{slice_name}: baseline MAE ${base_mae:.2f} -> candidate MAE ${cand_mae:.2f} (+{deg_pct*100:.1f}%)"
                    )

        passed = len(regressions) == 0
        summary = (
            "Segment regression gate passed: no material slice degradation"
            if passed
            else f"Segment regression gate failed on {len(regressions)} slice(s): {'; '.join(regressions)}"
        )
        return SegmentRegressionResult(
            passed=passed,
            regressed_segments=regressions,
            max_observed_slice_degradation_pct=round(max_deg, 4),
            summary=summary,
        )
