"""Vehicle taxonomy: normalization, alias resolution, and reference data.

The ``vehicle_taxonomy`` table (see persistence) is the system of record for
canonical makes/models/trims and their aliases. This module keeps the pure
normalization/resolution logic so it can be unit-tested without a database.

Milestone M8 expanded coverage to Heavy-Duty pickup families and Alberta regions.
Milestone M9 delivers Full Multi-Category Expansion (SUVs, Crossovers, Sedans,
Coupes, Vans, Hatchbacks, Pickups) across Alberta.
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
    #: Optional category: "pickup" | "suv" | "sedan" | "coupe" | "van" | "hatchback"
    category: str | None = None

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
        norm_raw = normalize_token(raw)
        for node in self.nodes:
            if node.level != "model" or node.parent_canonical != make_canonical:
                continue
            if norm_raw in [normalize_token(n) for n in node.all_names()]:
                return node.canonical_name
        return None

    def resolve_trim(self, model_canonical: str, raw: object) -> str | None:
        """Resolve a trim name within one canonical model (None when unknown)."""
        norm_raw = normalize_token(raw)
        for node in self.nodes:
            if node.level != "trim" or node.parent_canonical != model_canonical:
                continue
            if norm_raw in [normalize_token(n) for n in node.all_names()]:
                return node.canonical_name
        return None

    def resolve_region(self, raw: object) -> str | None:
        """Resolve an Alberta regional sub-market string (None when unknown)."""
        node = self._alias_map("region").get(normalize_token(raw))
        return node.canonical_name if node else None

    def resolve_category(self, make_canonical: str, model_canonical: str) -> str | None:
        """Resolve the vehicle category for a given canonical make and model."""
        for node in self.nodes:
            if (
                node.level == "model"
                and node.parent_canonical == make_canonical
                and node.canonical_name == model_canonical
            ):
                return node.category
        return None

    def known_models_for_make(self, make_canonical: str) -> tuple[str, ...]:
        return tuple(
            n.canonical_name
            for n in self.nodes
            if n.level == "model" and n.parent_canonical == make_canonical
        )

    def known_models_by_category(self, category: str) -> dict[str, tuple[str, ...]]:
        """Return a mapping of make -> tuple of models for a specific vehicle category."""
        result: dict[str, list[str]] = {}
        for n in self.nodes:
            if n.level == "model" and (category == "all" or n.category == category) and n.parent_canonical:
                result.setdefault(n.parent_canonical, []).append(n.canonical_name)
        return {k: tuple(v) for k, v in result.items()}

    @classmethod
    def from_nodes(cls, nodes: list[TaxonomyNode]) -> PickupTaxonomy:
        return cls(nodes=list(nodes))


# Backwards compatibility alias
VehicleTaxonomyDomain = PickupTaxonomy


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
    """Reference pickup taxonomy including Mid-Size, Half-Ton, and Heavy-Duty."""
    return [
        # Makes
        TaxonomyNode(level="make", canonical_name="ford"),
        TaxonomyNode(level="make", canonical_name="chevrolet", aliases=("chevy",)),
        TaxonomyNode(level="make", canonical_name="gmc"),
        TaxonomyNode(level="make", canonical_name="ram", aliases=("dodge ram", "ram trucks")),
        TaxonomyNode(level="make", canonical_name="dodge"),
        TaxonomyNode(level="make", canonical_name="toyota"),
        TaxonomyNode(level="make", canonical_name="nissan"),
        TaxonomyNode(level="make", canonical_name="jeep"),
        TaxonomyNode(level="make", canonical_name="honda"),

        # Ford Pickup Models
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="ranger", category="pickup"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="f-150", aliases=("f150", "f 150"), category="pickup"),
        TaxonomyNode(
            level="model",
            parent_canonical="ford",
            canonical_name="super duty f-250",
            aliases=("f-250", "f250", "f 250", "super duty 250"),
            category="pickup",
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="ford",
            canonical_name="super duty f-350",
            aliases=("f-350", "f350", "f 350", "super duty 350"),
            category="pickup",
        ),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="maverick", category="pickup"),

        # Chevrolet Pickup Models
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado",
            aliases=("silverado 1500", "1500"),
            category="pickup",
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado 2500hd",
            aliases=("silverado 2500", "2500hd", "2500"),
            category="pickup",
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="chevrolet",
            canonical_name="silverado 3500hd",
            aliases=("silverado 3500", "3500hd", "3500"),
            category="pickup",
        ),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="colorado", category="pickup"),

        # GMC Pickup Models
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra",
            aliases=("sierra 1500",),
            category="pickup",
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra 2500hd",
            aliases=("sierra 2500",),
            category="pickup",
        ),
        TaxonomyNode(
            level="model",
            parent_canonical="gmc",
            canonical_name="sierra 3500hd",
            aliases=("sierra 3500",),
            category="pickup",
        ),
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="canyon", category="pickup"),

        # Ram Pickup Models
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="1500", aliases=("ram 1500", "ram 1500 pickup", "ram 1500 classic"), category="pickup"),
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="2500", aliases=("ram 2500", "ram 2500 heavy duty"), category="pickup"),
        TaxonomyNode(level="model", parent_canonical="ram", canonical_name="3500", aliases=("ram 3500", "ram 3500 heavy duty"), category="pickup"),

        # Toyota Pickup Models
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="tacoma", category="pickup"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="tundra", category="pickup"),

        # Nissan Pickup Models
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="frontier", category="pickup"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="titan", category="pickup"),

        # Jeep & Honda Pickups
        TaxonomyNode(level="model", parent_canonical="jeep", canonical_name="gladiator", category="pickup"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="ridgeline", category="pickup"),

        # Trims - Ranger
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="xlt", aliases=("xlt fx4", "fx4")),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="raptor"),
        TaxonomyNode(level="trim", parent_canonical="ranger", canonical_name="tremor"),

        # Trims - F-150
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="xlt"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="king ranch"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="platinum"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="tremor"),
        TaxonomyNode(level="trim", parent_canonical="f-150", canonical_name="raptor"),

        # Trims - Super Duty
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="xl"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="xlt"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="lariat"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="king ranch"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="platinum"),
        TaxonomyNode(level="trim", parent_canonical="super duty f-250", canonical_name="limited"),

        # Trims - Silverado
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="wt", aliases=("work truck",)),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="custom"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="lt"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="rst"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="ltz"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="high country"),
        TaxonomyNode(level="trim", parent_canonical="silverado", canonical_name="zr2"),

        # Trims - Sierra
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="pro"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="sle"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="elevation"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="slt"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="at4"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="at4x"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="denali"),
        TaxonomyNode(level="trim", parent_canonical="sierra", canonical_name="denali ultimate"),

        # Trims - Ram 1500
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="tradesman"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="big horn", aliases=("lone star",)),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="laramie"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="rebel"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="1500", canonical_name="trx"),

        # Trims - Tacoma
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="sr"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="sr5"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd sport"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd off-road", aliases=("trd off road",)),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="tacoma", canonical_name="trd pro"),

        # Regional Taxonomy nodes
        *seed_alberta_regions(),
    ]


def seed_full_alberta_taxonomy() -> list[TaxonomyNode]:
    """Expanded multi-category reference taxonomy across all Alberta market segments (M9)."""
    pickup_nodes = seed_pickup_taxonomy()

    additional_nodes = [
        # Additional Makes
        TaxonomyNode(level="make", canonical_name="hyundai"),
        TaxonomyNode(level="make", canonical_name="volkswagen", aliases=("vw",)),
        TaxonomyNode(level="make", canonical_name="kia"),
        TaxonomyNode(level="make", canonical_name="bmw"),
        TaxonomyNode(level="make", canonical_name="mazda"),
        TaxonomyNode(level="make", canonical_name="subaru"),
        TaxonomyNode(level="make", canonical_name="audi"),
        TaxonomyNode(level="make", canonical_name="buick"),
        TaxonomyNode(level="make", canonical_name="chrysler"),
        TaxonomyNode(level="make", canonical_name="cadillac"),
        TaxonomyNode(level="make", canonical_name="mitsubishi"),
        TaxonomyNode(level="make", canonical_name="lexus"),
        TaxonomyNode(level="make", canonical_name="acura"),
        TaxonomyNode(level="make", canonical_name="infiniti"),
        TaxonomyNode(level="make", canonical_name="volvo"),
        TaxonomyNode(level="make", canonical_name="lincoln"),
        TaxonomyNode(level="make", canonical_name="mercedes-benz", aliases=("mercedes", "benz")),

        # ==========================================
        # SUVs & Crossovers
        # ==========================================
        # Ford SUVs
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="escape", category="suv"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="explorer", category="suv"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="edge", category="suv"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="expedition", category="suv"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="bronco", category="suv"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="bronco sport", category="suv"),

        # Toyota SUVs
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="rav4", category="suv"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="highlander", category="suv"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="4runner", category="suv"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="venza", category="suv"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="sequoia", category="suv"),

        # Jeep SUVs
        TaxonomyNode(level="model", parent_canonical="jeep", canonical_name="grand cherokee", category="suv"),
        TaxonomyNode(level="model", parent_canonical="jeep", canonical_name="cherokee", category="suv"),
        TaxonomyNode(level="model", parent_canonical="jeep", canonical_name="wrangler", category="suv"),
        TaxonomyNode(level="model", parent_canonical="jeep", canonical_name="compass", category="suv"),

        # Chevrolet SUVs
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="equinox", category="suv"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="traverse", category="suv"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="tahoe", category="suv"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="suburban", category="suv"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="blazer", category="suv"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="trax", category="suv"),

        # GMC SUVs
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="terrain", category="suv"),
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="acadia", category="suv"),
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="yukon", category="suv"),
        TaxonomyNode(level="model", parent_canonical="gmc", canonical_name="yukon xl", category="suv"),

        # Honda SUVs
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="cr-v", aliases=("crv", "cr v"), category="suv"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="pilot", category="suv"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="hr-v", aliases=("hrv", "hr v"), category="suv"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="passport", category="suv"),

        # Hyundai SUVs
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="santa fe", category="suv"),
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="tucson", category="suv"),
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="kona", category="suv"),
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="palisade", category="suv"),

        # Nissan SUVs
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="rogue", category="suv"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="murano", category="suv"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="pathfinder", category="suv"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="kicks", category="suv"),

        # Volkswagen SUVs
        TaxonomyNode(level="model", parent_canonical="volkswagen", canonical_name="tiguan", category="suv"),
        TaxonomyNode(level="model", parent_canonical="volkswagen", canonical_name="atlas", category="suv"),

        # Kia SUVs
        TaxonomyNode(level="model", parent_canonical="kia", canonical_name="sorento", category="suv"),
        TaxonomyNode(level="model", parent_canonical="kia", canonical_name="sportage", category="suv"),
        TaxonomyNode(level="model", parent_canonical="kia", canonical_name="telluride", category="suv"),

        # Mazda SUVs
        TaxonomyNode(level="model", parent_canonical="mazda", canonical_name="cx-5", aliases=("cx5", "cx 5"), category="suv"),
        TaxonomyNode(level="model", parent_canonical="mazda", canonical_name="cx-9", aliases=("cx9", "cx 9"), category="suv"),
        TaxonomyNode(level="model", parent_canonical="mazda", canonical_name="cx-30", aliases=("cx30", "cx 30"), category="suv"),

        # Subaru SUVs
        TaxonomyNode(level="model", parent_canonical="subaru", canonical_name="outback", category="suv"),
        TaxonomyNode(level="model", parent_canonical="subaru", canonical_name="forester", category="suv"),
        TaxonomyNode(level="model", parent_canonical="subaru", canonical_name="crosstrek", category="suv"),

        # BMW SUVs
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="x3", category="suv"),
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="x5", category="suv"),
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="x1", category="suv"),

        # Audi SUVs
        TaxonomyNode(level="model", parent_canonical="audi", canonical_name="q5", category="suv"),
        TaxonomyNode(level="model", parent_canonical="audi", canonical_name="q7", category="suv"),
        TaxonomyNode(level="model", parent_canonical="audi", canonical_name="q3", category="suv"),

        # Dodge SUVs
        TaxonomyNode(level="model", parent_canonical="dodge", canonical_name="durango", category="suv"),
        TaxonomyNode(level="model", parent_canonical="dodge", canonical_name="journey", category="suv"),

        # ==========================================
        # Sedans
        # ==========================================
        # Honda Sedans
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="civic", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="accord", category="sedan"),

        # Toyota Sedans
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="camry", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="corolla", category="sedan"),

        # Hyundai Sedans
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="elantra", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="sonata", category="sedan"),

        # Nissan Sedans
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="sentra", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="nissan", canonical_name="altima", category="sedan"),

        # Chevrolet Sedans
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="cruze", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="malibu", category="sedan"),

        # Volkswagen Sedans
        TaxonomyNode(level="model", parent_canonical="volkswagen", canonical_name="jetta", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="volkswagen", canonical_name="passat", category="sedan"),

        # BMW Sedans
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="3 series", aliases=("328i", "330i", "335i", "340i"), category="sedan"),
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="5 series", aliases=("528i", "530i", "535i", "540i"), category="sedan"),

        # Audi Sedans
        TaxonomyNode(level="model", parent_canonical="audi", canonical_name="a4", category="sedan"),
        TaxonomyNode(level="model", parent_canonical="audi", canonical_name="a6", category="sedan"),

        # ==========================================
        # Coupes & Sports Cars
        # ==========================================
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="mustang", category="coupe"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="camaro", category="coupe"),
        TaxonomyNode(level="model", parent_canonical="chevrolet", canonical_name="corvette", category="coupe"),
        TaxonomyNode(level="model", parent_canonical="dodge", canonical_name="challenger", category="coupe"),
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="4 series", aliases=("428i", "430i", "435i", "440i", "m4"), category="coupe"),
        TaxonomyNode(level="model", parent_canonical="bmw", canonical_name="2 series", aliases=("228i", "230i", "m2"), category="coupe"),
        TaxonomyNode(level="model", parent_canonical="subaru", canonical_name="brz", category="coupe"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="gr86", aliases=("86", "gt86", "supra"), category="coupe"),

        # ==========================================
        # Vans & Minivans
        # ==========================================
        TaxonomyNode(level="model", parent_canonical="dodge", canonical_name="grand caravan", aliases=("caravan",), category="van"),
        TaxonomyNode(level="model", parent_canonical="chrysler", canonical_name="pacifica", category="van"),
        TaxonomyNode(level="model", parent_canonical="chrysler", canonical_name="town & country", aliases=("town and country",), category="van"),
        TaxonomyNode(level="model", parent_canonical="honda", canonical_name="odyssey", category="van"),
        TaxonomyNode(level="model", parent_canonical="toyota", canonical_name="sienna", category="van"),
        TaxonomyNode(level="model", parent_canonical="ford", canonical_name="transit", aliases=("transit connect",), category="van"),

        # ==========================================
        # Hatchbacks
        # ==========================================
        TaxonomyNode(level="model", parent_canonical="volkswagen", canonical_name="golf", aliases=("golf gti", "gti", "golf r"), category="hatchback"),
        TaxonomyNode(level="model", parent_canonical="mazda", canonical_name="mazda3", aliases=("3", "mazda 3"), category="hatchback"),
        TaxonomyNode(level="model", parent_canonical="hyundai", canonical_name="elantra gt", aliases=("veloster",), category="hatchback"),
        TaxonomyNode(level="model", parent_canonical="kia", canonical_name="soul", category="hatchback"),

        # ==========================================
        # Trims for popular expanded models
        # ==========================================
        # Escape Trims
        TaxonomyNode(level="trim", parent_canonical="escape", canonical_name="s"),
        TaxonomyNode(level="trim", parent_canonical="escape", canonical_name="se"),
        TaxonomyNode(level="trim", parent_canonical="escape", canonical_name="sel"),
        TaxonomyNode(level="trim", parent_canonical="escape", canonical_name="titanium"),

        # Explorer Trims
        TaxonomyNode(level="trim", parent_canonical="explorer", canonical_name="base"),
        TaxonomyNode(level="trim", parent_canonical="explorer", canonical_name="xlt"),
        TaxonomyNode(level="trim", parent_canonical="explorer", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="explorer", canonical_name="st"),
        TaxonomyNode(level="trim", parent_canonical="explorer", canonical_name="platinum"),

        # RAV4 Trims
        TaxonomyNode(level="trim", parent_canonical="rav4", canonical_name="le"),
        TaxonomyNode(level="trim", parent_canonical="rav4", canonical_name="xle"),
        TaxonomyNode(level="trim", parent_canonical="rav4", canonical_name="xse"),
        TaxonomyNode(level="trim", parent_canonical="rav4", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="rav4", canonical_name="trail", aliases=("adventure",)),

        # Civic Trims
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="lx"),
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="ex"),
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="sport"),
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="touring"),
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="si"),
        TaxonomyNode(level="trim", parent_canonical="civic", canonical_name="type r"),

        # Grand Cherokee Trims
        TaxonomyNode(level="trim", parent_canonical="grand cherokee", canonical_name="laredo"),
        TaxonomyNode(level="trim", parent_canonical="grand cherokee", canonical_name="limited"),
        TaxonomyNode(level="trim", parent_canonical="grand cherokee", canonical_name="trailhawk"),
        TaxonomyNode(level="trim", parent_canonical="grand cherokee", canonical_name="overland"),
        TaxonomyNode(level="trim", parent_canonical="grand cherokee", canonical_name="summit"),

        # CR-V Trims
        TaxonomyNode(level="trim", parent_canonical="cr-v", canonical_name="lx"),
        TaxonomyNode(level="trim", parent_canonical="cr-v", canonical_name="ex"),
        TaxonomyNode(level="trim", parent_canonical="cr-v", canonical_name="ex-l"),
        TaxonomyNode(level="trim", parent_canonical="cr-v", canonical_name="touring"),
        TaxonomyNode(level="trim", parent_canonical="cr-v", canonical_name="sport"),

        # Mustang Trims
        TaxonomyNode(level="trim", parent_canonical="mustang", canonical_name="ecoboost"),
        TaxonomyNode(level="trim", parent_canonical="mustang", canonical_name="gt"),
        TaxonomyNode(level="trim", parent_canonical="mustang", canonical_name="mach 1"),
        TaxonomyNode(level="trim", parent_canonical="mustang", canonical_name="shelby gt500"),
    ]

    # Deduplicate makes across lists
    seen_makes: set[str] = set()
    deduped_nodes: list[TaxonomyNode] = []
    for node in [*pickup_nodes, *additional_nodes]:
        if node.level == "make":
            if node.canonical_name in seen_makes:
                continue
            seen_makes.add(node.canonical_name)
        deduped_nodes.append(node)

    return deduped_nodes
