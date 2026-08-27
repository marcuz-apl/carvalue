# 012: Milestone M9 — Full Alberta Multi-Category Expansion (SUVs, Crossovers, Sedans, Coupes, Vans, Hatchbacks)

**Date**: 2026-08-27  
**Author**: Antigravity / Engineering Team  
**Component**: `carvalue_core.taxonomy`, `carvalue_api`, `apps/web/`, `tests/`  
**Status**: Production / Verified (90/90 Tests Passing)

---

## 1. Overview & Objectives

Milestone M9 expands CarValue beyond its initial pickup focus into a **Full Alberta Multi-Category Asking-Price Valuator**. Leveraging the pre-ingested 44,412 Alberta dealer vehicle observations, the application now supports canonical reference data, valuation requests, prediction intervals, and UI categorization for:
- **🛻 Pickup Trucks** (7,642 listings): Ford F-150/Super Duty/Ranger/Maverick, Ram 1500/2500/3500, Chevrolet Silverado/Colorado, GMC Sierra/Canyon, Toyota Tacoma/Tundra, Nissan Frontier/Titan.
- **🚙 SUVs & Crossovers** (21,890 listings): Ford Escape/Explorer/Edge, Toyota RAV4/Highlander/4Runner, Jeep Grand Cherokee/Wrangler/Cherokee, Honda CR-V/Pilot, Hyundai Santa Fe/Tucson/Kona, Chevrolet Equinox/Traverse/Tahoe, GMC Terrain/Yukon, VW Tiguan/Atlas, Kia Sorento/Sportage, Mazda CX-5/CX-9, BMW X3/X5, Audi Q5.
- **🚗 Sedans** (7,631 listings): Honda Civic/Accord, Toyota Camry/Corolla, Hyundai Elantra/Sonata, Chevrolet Cruze/Malibu, Nissan Sentra/Altima, VW Jetta/Passat, BMW 3 Series/5 Series, Audi A4/A6.
- **🏎️ Coupes & Sports** (1,243 listings): Ford Mustang, Chevrolet Camaro/Corvette, Dodge Challenger, BMW 4 Series/2 Series, Toyota GR86, Subaru BRZ.
- **🚐 Vans & Minivans** (2,006 listings): Dodge Grand Caravan, Chrysler Pacifica/Town & Country, Honda Odyssey, Toyota Sienna, Ford Transit.
- **🚘 Hatchbacks** (3,177 listings): VW Golf/GTI/Golf R, Mazda3, Hyundai Elantra GT/Veloster, Kia Soul, Honda Civic Hatchback.

---

## 2. Technical Architecture & Changes

### 2.1 Pure Domain Taxonomy (`packages/core/carvalue_core/taxonomy.py`)
- Added `category` field to `TaxonomyNode` (`"pickup" | "suv" | "sedan" | "coupe" | "van" | "hatchback"`).
- Implemented `seed_full_alberta_taxonomy()` containing canonical models, trims, and alias normalization for all major Alberta vehicle classes.
- Added domain helper methods:
  - `resolve_category(make, model)`
  - `known_models_by_category(category)`

### 2.2 CLI & Database Seeding (`services/api/carvalue_api/cli.py`)
- Updated `do_init_db()` and `_seed_db()` to seed the full multi-category vehicle taxonomy and preserve category metadata in `aliases_json`.

### 2.3 Valuation API (`services/api/carvalue_api/__init__.py`)
- `/v1/taxonomy`: returns `models_by_category` dictionary mapping vehicle category to makes and canonical models.
- `/v1/valuations`: resolves vehicle category from taxonomy or request and populates the `category` attribute in `ValuationResponse`.

### 2.4 Web UI (`apps/web/`)
- `ValuationForm.tsx`: interactive category drop-down selector with cascading make/model/trim updates and live category vehicle counts.
- `ValuationResult.tsx`: dynamic category badge pill rendering alongside dataset provenance.

---

## 3. Verification & Test Evidence

- **Unit & Integration Suite**: `tests/test_multi_category_expansion.py` (6 tests covering SUV, Sedan, Coupe, Van, Hatchback taxonomy, category filtering, API responses, and slice regression gate evaluation).
- **Full Suite**: 90/90 tests passing (`.venv/bin/pytest`).
- **Production Build**: `npm run build` succeeds cleanly.
