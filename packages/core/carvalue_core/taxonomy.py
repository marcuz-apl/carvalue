"""Vehicle taxonomy: normalization, alias resolution, and reference data.

The ``vehicle_taxonomy`` table (see persistence) is the system of record for
canonical makes/models/trims and their aliases. This module keeps the pure
normalization/resolution logic so it can be unit-tested without a database.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def normalize_token(value: object) -> str:
    """Normalize free text for comparison: NFKD-fold accents, lowercase, collapse spaces."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().lower()
    # Trailing punctuation is noise in spreadsheet cells ("Ranger.", "(AB)").
    return text.strip(" \t.,;:!?-")


@dataclass(frozen=True)
class TaxonomyNode:
    """One canonical taxonomy entry with its accepted aliases."""

    level: str  # "make" | "model" | "trim"
    canonical_name: str
    aliases: tuple[str, ...] = ()
    #: For models: the make they belong to. For trims: the model they belong to.
    parent_canonical: str | None = None

    def all_names(self) -> tuple[str, ...]:
        return (self.canonical_name, *self.aliases)


@dataclass
class PickupTaxonomy:
    """In-memory view of the vehicle_taxonomy table for one import/valuation pass."""

    nodes: list[TaxonomyNode] = field(default_factory=list)

    def _alias_map(self, level: str) -> dict[str, TaxonomyNode]:
        return {
            name: node for node in self.nodes if node.level == level for name in node.all_names()
        }

    def resolve_make(self, raw: object) -> str | None:
        """Resolve a raw make string to its canonical form (None when unknown)."""
        node = self._alias_map("make").get(normalize_token(raw))
        return node.canonical_name if node else None

    def resolve_model(self, make_canonical: str, raw: object) -> str | None:
        """Resolve a model name within one canonical make (None when unknown)."""
        for node in self.nodes:
            if node.level != "model" or node.parent_canonical != make_canonical:
                continue
            if normalize_token(raw) in node.all_names():
                return node.canonical_name
        return None

    def resolve_trim(self, model_canonical: str, raw: object) -> str | None:
        """Resolve a trim name within one canonical model (None when unknown)."""
        for node in self.nodes:
            if node.level != "trim" or node.parent_canonical != model_canonical:
                continue
            if normalize_token(raw) in node.all_names():
                return node.canonical_name
        return None

    def known_models_for_make(self, make_canonical: str) -> tuple[str, ...]:
        return tuple(
            n.canonical_name
            for n in self.nodes
            if n.level == "model" and n.parent_canonical == make_canonical
        )

    @classmethod
    def from_nodes(cls, nodes: list[TaxonomyNode]) -> PickupTaxonomy:
        return cls(nodes=list(nodes))


def seed_pickup_taxonomy() -> list[TaxonomyNode]:
    """Initial reference pickup taxonomy loaded by ``carvalue init-db``.

    Deliberately small and documented: the MVP launch cohort starts with the
    Ford Ranger (PRD section 15, open decision 3) plus two common Alberta
    pickups so that import validation can reject non-pickups / foreign makes.
    Trims are listed where they appear in source data; listings may still have
    a null trim when the source does not provide one.
    """
    return [
        # Makes
        TaxonomyNode(level="make", canonical_name="ford"),
        TaxonomyNode(level="make", canonical_name="chevrolet", aliases=("chevy",)),
        TaxonomyNode(level="make", canonical_name="toyota"),
        # Models (pickups only)
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="ranger"),
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado",
            aliases=("silverado 1500", "silverado 2500hd", "silverado 3500hd"),
        ),
        # Trims
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="xl"),
        TaxonomyNode(
            level="trim", parent_canonical="ranger", canonical_name="xlt", aliases=("xlt fx4",)
        ),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="lariat"),
    ]
