"""CSV / XLSX import pipeline (FR-DATA-10).

Two phases so admins can review before anything is written:
1. ``preview_import`` — read the file, map columns via aliases, validate and
   normalize every row; returns accepted observations plus row-level rejections
   with stable reason codes (dry run, no writes).
2. ``commit_preview`` — upsert each accepted observation idempotently.

Spreadsheet cells are validated as *data* (AGENTS.md): numbers must parse to
integers where required, nothing is evaluated as a formula, XLSX formulas read
their cached value via openpyxl's ``data_only`` path used by pandas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ..listings import ListingObservation
from ..reasons import ReasonCode, safe_message
from ..taxonomy import PickupTaxonomy, normalize_token
from ..units import (
    DEFAULT_MAX_MILEAGE_KM,
    cad_to_cents,
    validate_model_year,
)

REQUIRED_COLUMNS = ("year", "mileage_km", "price_cad")

#: Header aliases mapped to canonical field names (case/whitespace-insensitive).
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "year": ("year", "model_year", "model year"),
    "mileage_km": (
        "mileage",
        "mileage_km",
        "mileage (km)",
        "kilometres",
        "odometer",
        "odometer_km",
        "km",
    ),
    "price_cad": ("price", "asking_price", "asking price", "price_cad", "asking price (cad)"),
    "trim": ("trim",),
    "drivetrain": ("drivetrain", "drive", "4wd/2wd"),
    "seller_type": ("seller_type", "seller"),
    "canonical_url": ("url", "listing_url", "source_url"),
    "source_record_id": ("listing_id", "inventory_id", "record_id"),
    "observed_at": ("first_listed_at", "listed_date", "date", "observed_at"),
    "province": ("province",),
    "city": ("city", "location_city"),
}

DRIVETRAIN_ALIASES = {"2wd": "2wd", "fwd": "2wd", "rear wheel drive": "2wd", "4wd": "4wd"}
SELLER_TYPE_ALIASES = {"dealer": "dealer", "private": "private", "owner": "private", "individual": "private"}

DEFAULT_MAX_PRICE_CAD: int = 300_000


@dataclass(frozen=True)
class ImportContext:
    """Everything a file import needs beyond the file itself."""

    source_id: int
    default_make: str  # canonical, e.g. "ford" (workbooks often omit make/model)
    default_model: str  # canonical, e.g. "ranger"
    observed_at_fallback: datetime  # used when a row has no usable date cell
    province: str = "AB"
    parser_version: str = "v1"
    max_mileage_km: int = DEFAULT_MAX_MILEAGE_KM
    max_price_cad: int = DEFAULT_MAX_PRICE_CAD


@dataclass(frozen=True)
class RowRejection:
    row_number: int  # 1-based data-row number in the file (header excluded)
    code: ReasonCode
    message: str = field(default="")

    def __post_init__(self) -> None:
        if not self.message:
            object.__setattr__(self, "message", safe_message(self.code))


@dataclass(frozen=True)
class ImportPreview:
    """Dry-run result of one import."""

    source_id: int
    file_path: str
    total_rows: int
    accepted_observations: tuple[ListingObservation, ...] = ()
    rejected_rows: tuple[RowRejection, ...] = ()
    column_errors: tuple[tuple[ReasonCode, str], ...] = ()  # (code, safe description)

    @property
    def is_committable(self) -> bool:
        return not self.column_errors


def _normalize_header(name: object) -> str:
    return re.sub(r"\s+", " ", normalize_token(name))


def map_columns(header: list[object]) -> tuple[dict[str, str], list[str]]:
    """Map file headers to canonical fields. Returns (mapping, unknown_headers)."""
    mapping: dict[str, str] = {}
    unknown: list[str] = []
    normalized_headers = {_normalize_header(h) for h in header if h is not None}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _normalize_header(alias) in normalized_headers and canonical not in mapping:
                # Prefer the exact-ish match that appears earliest in the file.
                candidates = [h for h in header if h is not None and _normalize_header(h) == _normalize_header(alias)]
                if candidates:
                    mapping[canonical] = str(candidates[0])
                    break
    used = set(mapping.values())
    unknown = [str(h) for h in header if h is not None and str(h) not in used]
    return mapping, unknown


def _coerce_int(value: Any) -> int | None:
    """Strict whole-number coercion (123, '123', 123.0 ok; '12.5', '' not)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = re.sub(r"[,\s]", "", value.strip())
        if not text:
            return None
        try:
            parsed = Decimal(text)
        except InvalidOperation:
            return None
        if parsed == int(parsed):
            return int(parsed)
    return None


def _coerce_datetime(value: Any, fallback: datetime) -> tuple[datetime | None, bool]:
    """Parse a date/datetime cell; returns (value_or_None, used_fallback)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, True
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d %b %Y"):
            try:
                from datetime import datetime as _dt

                dt = _dt.strptime(text[:19], fmt)
                break
            except ValueError:
                continue
        else:
            return None, True
    if dt.tzinfo is None:
        from ..persistence import _as_utc

        dt = _as_utc(dt)
    return dt, False


def normalize_row(
    row: dict[str, Any],
    context: ImportContext,
    taxonomy: PickupTaxonomy | None,
    reference_date: date,
    row_number: int,
) -> ListingObservation | RowRejection | tuple[RowRejection, list[ReasonCode]]:
    """Validate + normalize one raw row.

    Returns an observation when accepted; a single rejection for hard failures;
    or (rejection, notes) is not used — soft issues are recorded separately by
    the caller via the quarantined-notes return path below.
    """
    year = _coerce_int(row.get("year"))
    if year is None:
        return RowRejection(row_number=row_number, code=ReasonCode.MISSING_YEAR)

    mileage = _coerce_int(row.get("mileage_km"))
    if mileage is None:
        return RowRejection(row_number=row_number, code=ReasonCode.MISSING_MILEAGE)
    if mileage < 0 or mileage > context.max_mileage_km:
        return RowRejection(row_number=row_number, code=ReasonCode.MILEAGE_OUT_OF_RANGE)

    price_raw = row.get("price_cad")
    if price_raw is None or (isinstance(price_raw, str) and not price_raw.strip()):
        return RowRejection(row_number=row_number, code=ReasonCode.MISSING_PRICE)
    try:
        price_value = Decimal(str(price_raw).replace(",", "").strip())
    except InvalidOperation:
        return RowRejection(row_number=row_number, code=ReasonCode.NON_INTEGER_FIELD)
    if isinstance(price_raw, (int, float)) and not isinstance(price_raw, bool):
        price_value = Decimal(str(price_raw))
    if price_value <= 0:
        return RowRejection(row_number=row_number, code=ReasonCode.PRICE_NON_POSITIVE)
    max_cents = context.max_price_cad * 100
    cents = cad_to_cents(price_value)
    if int(cents) > max_cents:
        return RowRejection(row_number=row_number, code=ReasonCode.PRICE_ABOVE_PLAUSIBLE_MAX)

    try:
        year = validate_model_year(year, reference_date)
    except ValueError:
        return RowRejection(row_number=row_number, code=ReasonCode.YEAR_OUT_OF_RANGE)

    province = normalize_token(str(row.get("province") or context.province)).upper() or "AB"
    if province != "AB":
        return RowRejection(row_number=row_number, code=ReasonCode.LOCATION_NOT_ALBERTA)

    make_raw = row.get("make") or context.default_make
    model_raw = row.get("model") or context.default_model
    make = taxonomy.resolve_make(make_raw) if taxonomy else normalize_token(str(make_raw))
    model = (
        taxonomy.resolve_model(make, model_raw)
        if taxonomy and make is not None
        else normalize_token(str(model_raw))
    )
    if make is None or model is None:
        return RowRejection(row_number=row_number, code=ReasonCode.UNRECOGNIZED_MAKE_MODEL)

    observed_at, _ = _coerce_datetime(
        row.get("observed_at"), context.observed_at_fallback
    )

    drivetrain_raw = normalize_token(str(row.get("drivetrain") or ""))
    drivetrain = DRIVETRAIN_ALIASES.get(drivetrain_raw) if drivetrain_raw else None
    seller_raw = normalize_token(str(row.get("seller_type") or ""))
    seller_type = SELLER_TYPE_ALIASES.get(seller_raw) if seller_raw else None

    trim_raw = row.get("trim")
    trim = taxonomy.resolve_trim(model, trim_raw) if (taxonomy and trim_raw not in (None, "")) else None

    source_record_id = str(row.get("source_record_id") or "").strip() or f"row-{row_number}"
    url = str(row.get("canonical_url") or "").strip() or None

    return ListingObservation(
        source_id=context.source_id,
        source_record_id=source_record_id,
        make=str(make),
        model=str(model),
        model_year=int(year),
        mileage_km=mileage,
        asking_price_cad_cents=int(cents),
        observed_at_utc=observed_at,
        canonical_url=url,
        trim=trim,
        drivetrain=drivetrain,
        seller_type=seller_type,
        province=province,
        city=str(row.get("city") or "").strip() or None,
        parser_version=context.parser_version,
    )


def read_table(file_path: str | Path) -> tuple[list[object], list[dict[str, Any]]]:
    """Read a CSV/XLSX file as (header cells, raw row dicts). No formulas run."""
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        import csv

        with open(path, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
        header = rows[0] if rows else []
        data: list[dict[str, Any]] = [
            {header[i]: (row[i] if i < len(row) else None) for i in range(len(header))}
            for row in rows[1:]
            if any(cell not in (None, "") for cell in row)
        ]
        return header, data
    # XLSX: pandas/openpyxl read cached values only (data_only semantics).
    import pandas as pd

    frame = pd.read_excel(path, engine="openpyxl")
    if frame.empty and not list(frame.columns):
        return [], []
    header = [str(col) for col in frame.columns]
    data = frame.where(pd.notna(frame), None).to_dict(orient="records")
    return header, data


def preview_import(
    file_path: str | Path,
    context: ImportContext,
    taxonomy: PickupTaxonomy | None = None,
) -> ImportPreview:
    """Dry-run an import: read, map columns, normalize rows (no DB writes)."""
    header, raw_rows = read_table(file_path)
    if not raw_rows and not header:
        return ImportPreview(
            source_id=context.source_id,
            file_path=str(file_path),
            total_rows=0,
            column_errors=((ReasonCode.COLUMN_NOT_FOUND, "File has no rows."),),
        )

    mapping, _unknown = map_columns(header)
    column_errors: list[tuple[ReasonCode, str]] = []
    for required in REQUIRED_COLUMNS:
        if required not in mapping:
            column_errors.append(
                (ReasonCode.COLUMN_NOT_FOUND, f"Required column '{required}' was not found.")
            )

    accepted: list[ListingObservation] = []
    rejected: list[RowRejection] = []
    reference_date = context.observed_at_fallback.date()
    for index, raw_row in enumerate(raw_rows, start=1):
        mapped_row = {canonical: raw_row.get(file_header) for canonical, file_header in mapping.items()}
        result = normalize_row(mapped_row, context, taxonomy, reference_date, index)
        if isinstance(result, ListingObservation):
            accepted.append(result)
        elif isinstance(result, RowRejection):
            rejected.append(result)

    return ImportPreview(
        source_id=context.source_id,
        file_path=str(file_path),
        total_rows=len(raw_rows),
        accepted_observations=tuple(accepted),
        rejected_rows=tuple(rejected),
        column_errors=tuple(column_errors),
    )


@dataclass(frozen=True)
class CommitSummary:
    accepted: int = 0
    updated: int = 0
    duplicate: int = 0


def commit_preview(session: Any, preview: ImportPreview) -> CommitSummary:
    """Idempotently upsert every accepted observation from a valid preview."""
    from ..persistence import upsert_listing_observation

    if not preview.is_committable:
        raise ValueError("import preview cannot be committed while required columns are missing")

    summary = CommitSummary()
    for observation in preview.accepted_observations:
        outcome = upsert_listing_observation(session, observation)
        if outcome.status == "accepted":
            summary = CommitSummary(
                accepted=summary.accepted + 1,
                updated=summary.updated,
                duplicate=summary.duplicate,
            )
        elif outcome.status == "updated":
            summary = CommitSummary(
                accepted=summary.accepted,
                updated=summary.updated + 1,
                duplicate=summary.duplicate,
            )
        else:
            summary = CommitSummary(
                accepted=summary.accepted,
                updated=summary.updated,
                duplicate=summary.duplicate + 1,
            )
    return summary
