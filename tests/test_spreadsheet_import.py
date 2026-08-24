from datetime import UTC, datetime

import pytest
from carvalue_core.imports.spreadsheet import (
    ImportContext,
    ImportPreview,
    commit_preview,
    preview_import,
)
from carvalue_core.listings import ListingObservation
from carvalue_core.persistence import Base, make_engine
from carvalue_core.reasons import ReasonCode
from carvalue_core.taxonomy import PickupTaxonomy, seed_pickup_taxonomy


def test_preview_with_missing_required_column_cannot_commit(tmp_path) -> None:
    import_file = tmp_path / "missing-price.csv"
    import_file.write_text("Year,Mileage\n2022,40000\n", encoding="utf-8")
    context = ImportContext(
        source_id=1,
        default_make="ford",
        default_model="ranger",
        observed_at_fallback=datetime(2026, 8, 21, tzinfo=UTC),
    )

    preview = preview_import(
        import_file,
        context,
        PickupTaxonomy.from_nodes(seed_pickup_taxonomy()),
    )
    assert not preview.is_committable
    observation = ListingObservation(
        source_id=1,
        source_record_id="row-1",
        make="ford",
        model="ranger",
        model_year=2022,
        mileage_km=40_000,
        asking_price_cad_cents=3_000_000,
        observed_at_utc=context.observed_at_fallback,
    )
    preview = ImportPreview(
        source_id=preview.source_id,
        file_path=preview.file_path,
        total_rows=preview.total_rows,
        accepted_observations=(observation,),
        column_errors=(
            (ReasonCode.COLUMN_NOT_FOUND, "Required column 'price_cad' was not found."),
        ),
    )

    with pytest.raises(ValueError, match="cannot be committed"):
        commit_preview(None, preview)


def test_sqlite_schema_can_be_created(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'carvalue.db'}")
    Base.metadata.create_all(engine)
    engine.dispose()
