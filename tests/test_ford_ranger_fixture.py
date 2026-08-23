"""M1 contract test: the authorized Ford Ranger fixture rows normalize
deterministically into CAD cents, kilometres, and tz-aware UTC.

Roadmap M1 exit gate: "Ford Ranger fixture rows normalize deterministically in
CAD/km/UTC." Values here are read straight from the workbook's ``Year``,
``Mileage``, and ``Price`` columns (all CAD), so they must reproduce exactly on
every run — no fabricated precision, stable units at the boundary.
"""

import csv
from datetime import UTC, datetime

from carvalue_core.imports.spreadsheet import ImportContext, preview_import
from carvalue_core.listings import ListingObservation, listing_fingerprint
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy

FIXTURE = "tests/fixtures/ford-ranger/valid.csv"


def _workbook_values(path: str = FIXTURE) -> list[tuple[str, str, int, int, int]]:
    """(make, model, year, km, CAD cents) read straight from the workbook CSV."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))[1:]  # header excluded
    out: list[tuple[str, str, int, int, int]] = []
    for row in rows:
        year, mileage, price = row[0], row[1], row[2]
        out.append(("ford", "ranger", int(year), int(mileage), int(float(price)) * 100))
    return out


def _context() -> ImportContext:
    return ImportContext(
        source_id=1,
        default_make="ford",
        default_model="ranger",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
        province="AB",
    )


def _signature(preview) -> tuple:
    """Stable identity signature used to prove deterministic normalization."""
    return tuple(
        (
            o.make,
            o.model,
            o.model_year,
            o.mileage_km,
            o.asking_price_cad_cents,
            listing_fingerprint(o),
        )
        for o in preview.accepted_observations
    )


def test_ford_ranger_rows_normalize_in_cad_km_utc() -> None:
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    preview = preview_import(FIXTURE, _context(), taxonomy)

    assert not preview.column_errors, "authorized fixture must have no missing columns"
    expected = _workbook_values()
    assert len(preview.accepted_observations) == len(expected)

    for obs, (make, model, year, km, cents) in zip(
        preview.accepted_observations, expected, strict=True
    ):
        assert isinstance(obs, ListingObservation)
        # Canonical make/model/year.
        assert obs.make == make
        assert obs.model == model
        assert obs.model_year == year
        # CAD integer cents at the boundary (never binary float).
        assert obs.asking_price_cad_cents == cents
        assert isinstance(obs.asking_price_cad_cents, int)
        # Kilometres as a non-negative integer.
        assert obs.mileage_km == km
        assert isinstance(obs.mileage_km, int) and obs.mileage_km >= 0
        # tz-aware UTC observation time.
        assert obs.observed_at_utc.tzinfo is not None
        assert obs.observed_at_utc.utcoffset() is not None


def test_ford_ranger_normalization_is_deterministic() -> None:
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    first = preview_import(FIXTURE, _context(), taxonomy)
    second = preview_import(FIXTURE, _context(), taxonomy)
    assert _signature(first) == _signature(second)


def test_ford_ranger_contract_has_no_personal_data() -> None:
    """The normalized observation carries vehicle/listing facts only."""
    personal = {"seller_name", "seller_phone", "seller_email", "free_text", "photo_url"}
    assert not (personal & set(ListingObservation.__dataclass_fields__))
