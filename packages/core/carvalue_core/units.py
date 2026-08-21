"""Money and unit conventions at CarValue system boundaries.

Conventions (AGENTS.md / PRD):
- Money is **integer CAD cents** in storage and application logic; never a
  binary float for persisted currency.
- Odometer is a **non-negative integer number of kilometres**.
- Display rounding (nearest CAD 100) happens explicitly here, not implicitly
  at the UI boundary.
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import NewType

#: Typed integer cents of Canadian dollars. Transparent at runtime (NewType),
#: used to make money values explicit in signatures.
CadCents = NewType("CadCents", int)

CENTS_PER_CAD: int = 100
HUNDRED_CAD_IN_CENTS: int = CENTS_PER_CAD * 100

# Plausible input bounds (FR-PUB-02). Configurable at the API boundary later.
MIN_MILEAGE_KM: int = 0
DEFAULT_MAX_MILEAGE_KM: int = 800_000
DEFAULT_MIN_MODEL_YEAR: int = 2010

#: A model-year vehicle is treated as new on July 1st of its model year when a
#: reference date must be derived from the (year-granular) model year alone.
#: This keeps the baseline feature "vehicle age" anchored to the valuation /
#: observation date instead of an intercept on raw calendar years (FR-ML-01).
MODEL_YEAR_ANCHOR_MONTH: int = 7
MODEL_YEAR_ANCHOR_DAY: int = 1

DAYS_PER_YEAR: float = 365.25


def cad_to_cents(value: Decimal | float | int | str) -> CadCents:
    """Convert a CAD dollar amount to integer cents (round half-up)."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not math.isfinite(decimal_value):
        raise ValueError(f"price is not finite: {value!r}")
    cents = int((decimal_value * CENTS_PER_CAD).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return CadCents(cents)


def round_cad_to_nearest_100(cents: int | CadCents) -> int:
    """Round an integer-cent CAD amount to the nearest $100 (half-up).

    >>> round_cad_to_nearest_100(3_124_900)  # $31,249
    3120000
    """
    if cents < 0:
        raise ValueError(f"cents must be non-negative, got {cents}")
    return (int(cents) + HUNDRED_CAD_IN_CENTS // 2) // HUNDRED_CAD_IN_CENTS * HUNDRED_CAD_IN_CENTS


def format_cad(cents: int | CadCents) -> str:
    """Format integer cents as a display string, e.g. ``$31,200``."""
    dollars = int(int(cents) // CENTS_PER_CAD)
    return f"${dollars:,}"


def validate_mileage_km(value: object, max_km: int = DEFAULT_MAX_MILEAGE_KM) -> int:
    """Validate an odometer reading is a non-negative integer within bounds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"mileage must be an integer number of kilometres, got {value!r}")
    if value < MIN_MILEAGE_KM or value > max_km:
        raise ValueError(
            f"mileage {value} km outside plausible range [{MIN_MILEAGE_KM}, {max_km}] km"
        )
    return value


def validate_model_year(value: object, reference: date) -> int:
    """Validate a model year is within a plausible window around ``reference``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"model year must be an integer, got {value!r}")
    min_year = DEFAULT_MIN_MODEL_YEAR
    max_year = reference.year + 1
    if value < min_year or value > max_year:
        raise ValueError(f"model year {value} outside plausible range [{min_year}, {max_year}]")
    return value


def vehicle_age_years(model_year: int, reference: date) -> float:
    """Vehicle age in (fractional) years at ``reference``.

    Uses the July 1st-of-model-year anchor described above and clamps to zero
    so future-dated model years never produce negative ages.
    """
    anchor = date(model_year, MODEL_YEAR_ANCHOR_MONTH, MODEL_YEAR_ANCHOR_DAY)
    age_days = (reference - anchor).days
    return max(age_days / DAYS_PER_YEAR, 0.0)
