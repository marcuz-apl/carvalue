"""M1 contract test: the normalized source-neutral schema keeps personal seller
data and photos out of the contract, rejects arbitrary make/model strings, and
stably fails when a required field disappears.

Roadmap M1 exit gate items 3 & 4; PRD FR-DATA-03 (collect only valuation fields)
and FR-PUB-01 (valid normalized selections only).
"""

from datetime import UTC, datetime

from carvalue_core.imports.spreadsheet import ImportContext, preview_import
from carvalue_core.listings import ListingObservation
from carvalue_core.reasons import ReasonCode
from carvalue_core.source_policy import VALUATION_SAFE_PERMITTED_FIELDS
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy


def test_personal_fields_have_no_normalized_contract_path() -> None:
    """Permissioned field set and normalized schema both exclude personal data."""
    personal = {
        "seller_name",
        "seller_phone",
        "seller_email",
        "free_text",
        "photo_url",
        "vin",
    }
    assert not (personal & VALUATION_SAFE_PERMITTED_FIELDS)
    assert not (personal & set(ListingObservation.__dataclass_fields__))


def test_arbitrary_make_model_resolution_rejects_foreign() -> None:
    """FR-PUB-01: arbitrary make/model strings resolve to canonical or are rejected."""
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    # Known pickup resolves; foreign/sedan maker and wrong-name model return None.
    assert taxonomy.resolve_make("ford") == "ford"
    assert taxonomy.resolve_make("Cadillac") is None
    assert taxonomy.resolve_model("ford", "ranger") == "ranger"
    assert taxonomy.resolve_model("ford", "tucson") is None


def test_foreign_default_vehicle_rejected(tmp_path) -> None:
    """A bare workbook row whose canonical defaults are a sedan fails closed."""
    path = tmp_path / "bare.csv"
    path.write_text("Year,Mileage,Price\n2022,40000,30000\n", encoding="utf-8")
    context = ImportContext(
        source_id=1,
        default_make="cadillac",
        default_model="cts_sedan",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
    )
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    preview = preview_import(str(path), context, taxonomy)
    assert ReasonCode.UNRECOGNIZED_MAKE_MODEL in {r.code for r in preview.rejected_rows}


def test_required_column_disappearance_stable_failure(tmp_path) -> None:
    """FR-DATA-07 / scenario 5: a missing required column yields a stable code."""
    path = tmp_path / "no_price.csv"
    path.write_text("Year,Mileage\n2022,40000\n", encoding="utf-8")
    context = ImportContext(
        source_id=1,
        default_make="ford",
        default_model="ranger",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
    )
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    preview = preview_import(str(path), context, taxonomy)
    assert not preview.is_committable
    assert ReasonCode.COLUMN_NOT_FOUND in {c for c, _ in preview.column_errors}


def test_missing_price_row_stable_failure(tmp_path) -> None:
    """A row whose price cell disappears fails with a stable reason code."""
    path = tmp_path / "price.csv"
    path.write_text("Year,Mileage,Price\n2022,40000,\n", encoding="utf-8")
    context = ImportContext(
        source_id=1,
        default_make="ford",
        default_model="ranger",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
    )
    taxonomy = PickupTaxonomy.from_nodes(seed_pickup_taxonomy())
    preview = preview_import(str(path), context, taxonomy)
    assert ReasonCode.MISSING_PRICE in {r.code for r in preview.rejected_rows}
