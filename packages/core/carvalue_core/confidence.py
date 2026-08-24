"""Confidence / evidence labels and refusal rules.

Every valuation result carries one of High, Medium, Low or Insufficient Data.
The rules prefer ``Insufficient Data`` over fabricated precision for sparse,
stale, out-of-distribution, or weakly-bounded inputs (AGENTS.md guardrail).
All thresholds live in :class:`EvidenceConfig` so they are unit-testable and
configurable without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .reasons import ReasonCode


class ConfidenceLabel(str):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class EvidenceConfig:
    """Thresholds for confidence assignment and refusal (defaults are MVP policy)."""

    #: Below this many active comparables we refuse to produce a point estimate.
    min_comparables_for_estimate: int = 4
    #: PRD launch gate: >=50 useful comparables per supported family -> High eligible.
    high_confidence_min_comparables: int = 50
    medium_confidence_min_comparables: int = 15
    #: Relative interval half-width (hi - lo) / (2 * point). Above max => refuse,
    #: above low cap => at most Low confidence.
    max_interval_rel_width: float = 0.75
    low_interval_rel_width_cap: float = 0.45
    #: No comparables observed within this many days => data too stale to trust.
    stale_after_days: int = 90


@dataclass(frozen=True)
class ModelBounds:
    """Training-domain bounds recorded with a model artifact (FR-ML-10)."""

    min_model_year: int
    max_model_year: int
    min_mileage_km: int
    max_mileage_km: int


@dataclass(frozen=True)
class ConfidenceDecision:
    label: str  # one of ConfidenceLabel values
    #: Refusal/annotation codes that drove the decision (empty for clean High).
    notes: tuple[ReasonCode, ...] = field(default_factory=tuple)

    @property
    def is_refused(self) -> bool:
        return self.label == ConfidenceLabel.INSUFFICIENT_DATA


def relative_interval_width(low_cad_cents: int, point_cad_cents: int, high_cad_cents: int) -> float:
    """Relative half-width of a prediction interval as a fraction of the point."""
    if point_cad_cents <= 0:
        return float("inf")
    return (high_cad_cents - low_cad_cents) / (2.0 * point_cad_cents)


def _band_status(
    value: int,
    hard_lo: int,
    hard_hi: int,
    soft_lo: int,
    soft_hi: int,
) -> bool | None:
    """True inside the hard box, None inside a tolerance band, False beyond it."""
    if hard_lo <= value <= hard_hi:
        return True
    if soft_lo <= value <= soft_hi:
        return None
    return False


def out_of_training_domain(bounds: ModelBounds, model_year: int, mileage_km: int) -> bool | None:
    """Classify an input against training bounds.

    Returns ``True`` for a hard miss (refuse), ``False`` when inside the box,
    and ``None`` for a soft miss (downgrade to at most Low). Tolerance bands are
    one model year on either side and 25% beyond each mileage extreme.
    """
    year_status = _band_status(
        model_year,
        hard_lo=bounds.min_model_year,
        hard_hi=bounds.max_model_year,
        soft_lo=bounds.min_model_year - 1,
        soft_hi=bounds.max_model_year + 1,
    )
    mileage_status = _band_status(
        mileage_km,
        hard_lo=bounds.min_mileage_km,
        hard_hi=bounds.max_mileage_km,
        soft_lo=max(0, int(bounds.min_mileage_km * 0.75)),
        soft_hi=int(bounds.max_mileage_km * 1.25),
    )
    for status in (year_status, mileage_status):
        if status is False:
            return True
    if year_status is None or mileage_status is None:
        return None
    return False


def decide_confidence(
    *,
    comparables_count: int,
    data_freshness_days: float,
    interval_rel_width: float | None,
    ood: bool | None,
    config: EvidenceConfig | None = None,
    valuation_date: date | None = None,  # reserved for future seasonality rules
) -> ConfidenceDecision:
    """Apply the evidence rules in a fixed, documented order."""
    cfg = config or EvidenceConfig()
    refused: list[ReasonCode] = []
    caps_low: list[ReasonCode] = []

    if comparables_count < cfg.min_comparables_for_estimate:
        return ConfidenceDecision(ConfidenceLabel.INSUFFICIENT_DATA, (ReasonCode.SPARSE_SEGMENT,))
    if ood is True:
        refused.append(ReasonCode.OUT_OF_TRAINING_DOMAIN)
    elif ood is None:
        caps_low.append(ReasonCode.OUT_OF_TRAINING_DOMAIN)
    if data_freshness_days > cfg.stale_after_days:
        refused.append(ReasonCode.STALE_MODEL)
    if interval_rel_width is not None and interval_rel_width > cfg.max_interval_rel_width:
        refused.append(ReasonCode.TOO_WIDE_INTERVAL)
    elif interval_rel_width is not None and interval_rel_width > cfg.low_interval_rel_width_cap:
        caps_low.append(ReasonCode.TOO_WIDE_INTERVAL)

    if refused:
        return ConfidenceDecision(ConfidenceLabel.INSUFFICIENT_DATA, tuple(refused))

    label = ConfidenceLabel.LOW
    if comparables_count >= cfg.high_confidence_min_comparables:
        label = ConfidenceLabel.HIGH
    elif comparables_count >= cfg.medium_confidence_min_comparables:
        label = ConfidenceLabel.MEDIUM
    if caps_low and label != ConfidenceLabel.LOW:
        label = ConfidenceLabel.LOW
    return ConfidenceDecision(label, tuple(caps_low))
