"""Vehicle taxonomy: normalization, alias resolution, and reference data.

The ``vehicle_taxonomy`` table (see persistence) is the system of record for
canonical makes/models/trims and their aliases. This module keeps the pure
normalization/resolution logic so it can be unit-tested without a database.

Milestone M8 expands coverage to Heavy-Duty pickup families (F-250/F-350,
Silverado/Sierra 2500/3500 HD, Ram 2500/3500, Tundra, Titan) and Alberta regional
sub-markets.
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

    level: str  # "make" | "model" | "trim" | "region"
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

    def resolve_region(self, raw: object) -> str | None:
        """Resolve an Alberta regional sub-market string (None when unknown)."""
        node = self._alias_map("region").get(normalize_token(raw))
        return node.canonical_name if node else None

    def known_models_for_make(self, make_canonical: str) -> tuple[str, ...]:
        return tuple(
            n.canonical_name
            for n in self.nodes
            if n.level == "model" and n.parent_canonical == make_canonical
        )

    @classmethod
    def from_nodes(cls, nodes: list[TaxonomyNode]) -> PickupTaxonomy:
        return cls(nodes=list(nodes))


def seed_alberta_regions() -> list[TaxonomyNode]:
    """Alberta regional sub-markets for geographic slice evaluation."""
    return [
        TaxonomyNode(
            level="region",
            canonical_name="calgary_region",
            aliases=("calgary", "airdrie", "cochrane", "okotoks", "chestermere", "rocky view"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="edmonton_region",
            aliases=("edmonton", "st albert", "sherwood park", "leduc", "spruce grove", "strathcona"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="red_deer_central",
            aliases=("red deer", "sylvan lake", "lacombe", "ponoka", "blackfalds", "innisfail"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="lethbridge_south",
            aliases=("lethbridge", "coaldale", "taber", "cardston", "pincher creek"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="medicine_hat_southeast",
            aliases=("medicine hat", "brooks", "bow island"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="fort_mcmurray_north",
            aliases=("fort mcmurray", "wood buffalo", "cold lake"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="grande_prairie_peace",
            aliases=("grande prairie", "peace river", "fairview", "high level"),
        ),
        TaxonomyNode(
            level="region",
            canonical_name="rural_alberta",
            aliases=("rural", "other ab", "alberta rural"),
        ),
    ]


def seed_pickup_taxonomy() -> list[TaxonomyNode]:
    """Expanded reference pickup taxonomy including Mid-Size, Half-Ton, and Heavy-Duty (M8)."""
    return [
        # Makes
        TaxonomyNode(level="make", canonical_name="ford"),
        TaxonomyNode(level="make", canonical_name="chevrolet", aliases=("chevy",)),
        TaxonomyNode(level="make", canonical_name="gmc"),
        TaxonomyNode(level="make", canonical_name="ram", aliases=("dodge", "dodge ram")),
        TaxonomyNode(level="make", canonical_name="toyota"),
        TaxonomyNode(level="make", canonical_name="nissan"),

        # Ford Models
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="ranger"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="f-150", aliases=("f150", "f 150")),
        TaxonomyNode(
            level="model",
            parent_canonical="ford",
            canonical_name="super duty f-250",
            aliases=("f-250", "f250", "f 250", "super duty 250"),
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="ford",
            canonical_name="super duty f-350",
            aliases=("f-350", "f350", "f 350", "super duty 350"),
        ),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="maverick"),

        # Chevrolet Models
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado",
            aliases=("silverado 1500", "1500"),
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado 2500hd",
            aliases=("silverado 2500", "2500hd", "2500"),
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado 3500hd",
            aliases=("silverado 3500", "3500hd", "3500"),
        ),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="colorado"),

        # GMC Models
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra",
            aliases=("sierra 1500",),
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra 2500hd",
            aliases=("sierra 2500",),
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra 3500hd",
            aliases=("sierra 3500",),
        ),
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="canyon"),

        # Ram Models
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="1500"),
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="2500"),
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="3500"),

        # Toyota Models
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="tacoma"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="tundra"),

        # Nissan Models
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="frontier"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="titan"),

        # Ranger Trims
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="xlt", aliases=("xlt fx4", "fx4")),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="raptor"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="tremor"),

        # F-150 Trims
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="xlt"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="king ranch"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="platinum"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="tremor"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="raptor"),

        # Super Duty Trims
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="xlt"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="king ranch"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="platinum"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="limited"),

        # Silverado 1500 / 2500HD Trims
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="wt", aliases=("work truck",)),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="custom"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="lt"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="rst"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="ltz"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="high country"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="zr2"),

        # Sierra 1500 / 2500HD Trims
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="pro"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="sle"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="elevation"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="slt"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="at4"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="at4x"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="denali"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="denali ultimate"),

        # Ram 1500 / 2500 Trims
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="tradesman"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="big horn", aliases=("lone star",)),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="laramie"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="rebel"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="trx"),

        # Tacoma Trims
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="sr"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="sr5"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd sport"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd off-road", aliases=("trd off road",)),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd pro"),

        # Regional Taxonomy nodes
        *seed_alberta_regions(),
    ]
