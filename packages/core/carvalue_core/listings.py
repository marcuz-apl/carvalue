"""Normalized listing observations and conservative deduplication.

Dedup order (FR-DATA-06): source/source record ID first, then canonical URL,
then a conservative fingerprint of vehicle (+ dealer/location) attributes. The
fingerprint never includes the asking price because prices legitimately change
over the life of a listing; it only collapses observations that describe the
same vehicle with identical identity attributes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

FINGERPRINT_VERSION = "v1"


@dataclass(frozen=True)
class ListingObservation:
    """One normalized observation of one listing (upsertable)."""

    source_id: int
    source_record_id: str
    make: str  # canonical lowercase
    model: str  # canonical lowercase
    model_year: int
    mileage_km: int
    asking_price_cad_cents: int
    # datetime (tz-aware UTC); typed loosely to avoid core↔persistence cycle
    observed_at_utc: object
    #: Provenance and optional attributes ---------------------------------
    canonical_url: str | None = None
    trim: str | None = None  # canonical lowercase, when the source provides it
    drivetrain: str | None = None  # "2wd" | "4wd" | None
    seller_type: str | None = None  # "dealer" | "private" | None
    cab_style: str | None = None
    box_length_m: float | None = None
    province: str = "AB"
    city: str | None = None
    parser_version: str = "v1"
    content_checksum_sha256: str | None = None


def _normalize_url(url: str) -> str:
    """Canonicalize a URL for identity use (lowercase host, drop fragments/query)."""
    parts = urlsplit(url.strip())
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/"), "", "")).rstrip("/")


def listing_fingerprint(observation: ListingObservation) -> str:
    """Stable sha256 fingerprint of one listing's identity.

    Canonical URL wins over attribute hashing when present (dedup step 2);
    otherwise the conservative vehicle/location hash is used (dedup step 3).
    """
    if observation.canonical_url:
        payload = f"{FINGERPRINT_VERSION}|url|{_normalize_url(observation.canonical_url)}"
    else:
        parts = [
            FINGERPRINT_VERSION,
            "attrs",
            observation.make,
            observation.model,
            str(observation.model_year),
            str(observation.mileage_km),
            observation.trim or "-",
            observation.drivetrain or "-",
            observation.seller_type or "-",
            observation.cab_style or "-",
            f"{observation.box_length_m:.2f}" if observation.box_length_m else "-",
            observation.province,
            observation.city or "-",
        ]
        payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class UpsertOutcome:
    """Result of upserting one observation."""

    status: str  # "accepted" | "updated" | "duplicate"
    listing_id: int
    price_history_appended: bool = False
