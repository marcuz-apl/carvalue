# Technote: Real Dealer Data Ingestion, Price Aging Economics, Admin ML Studio & Unified Port 4020

**Date:** 2026-08-25  
**Author:** Antigravity / Engineering Team  
**Scope:** `packages/core/carvalue_core/`, `services/api/carvalue_api/`, `apps/web/`, `docs/`  
**Status:** Implemented, Tested, Verified, and Pushed (`origin/master`)  

---

## 1. Context & Problem Statement

Prior to this milestone, CarValue operated as an end-to-end prototype tested primarily with synthetic fixture files (`demo-ford-f150.csv`, `demo-ford-ranger.csv`). When testing vehicle models outside Ford Ranger/F-150, the system triggered the explainable refusal rule (*"Insufficient Market Evidence"*).

The objectives of this iteration were:
1. **Ingest Real Alberta Market Data:** Import and normalize the 307,000+ row Canadian dealer inventory dataset (`ca-dealers-used-2022.csv`), extracting all supported Alberta pickup listings.
2. **Implement Data Provenance & Scope Filters:** Differentiate between real 2022 dealer listings and synthetic benchmark samples across DB, API, and the Web UI.
3. **Formulate Price Aging Economics:** Formalize and document how historical 2022 market observations are mathematically mapped to 2026 current-year valuations.
4. **Build Dedicated Admin Portal & ML Studio:** Enable administrators to manage datasets, tune hyperparameters (inflation drift, refusal thresholds), train candidates, and promote models.
5. **Modernize Layout & Unify on Port 4020:** Align header and footer with organizational standards (mimicking `resologix.alfazen.org`) and unify the entire application under single entry point **Port 4020**.

---

## 2. Real Data Ingestion & Persistence Fixes

### 2.1 Persistence Layer Fix (`ListingPriceHistory` Generation)
In [`packages/core/carvalue_core/persistence.py`](file:///mnt/e/projects/CarValue/packages/core/carvalue_core/persistence.py), `upsert_listing_observation` was updated to ensure that when a brand-new listing is inserted, its initial price point is simultaneously written to `ListingPriceHistory`:

```python
# Initial Price Point on First Seen
history_entry = ListingPriceHistory(
    listing_id=listing.id,
    price_cents=price_cents,
    observed_at=observed_at,
)
session.add(history_entry)
```

### 2.2 Dataset Extraction & Breakdown
From `data-extra/ca-dealers-used-2022.csv` (307,126 Canadian dealer listings), **6,954 real Alberta pickup truck listings** were normalized into SQLite under source `ca-dealers-used-2022`:

| Make | Model | Real Alberta Observations |
|:---|:---|:---|
| **RAM** | Ram 1500 | **1,901** |
| **RAM** | Ram 2500 Heavy Duty | **365** |
| **RAM** | Ram 3500 Heavy Duty | **374** |
| **Ford** | Ford F-150 | **1,438** |
| **Ford** | Ford Super Duty F-350 | **284** |
| **Ford** | Ford Super Duty F-250 | **95** |
| **Ford** | Ford Ranger | **66** |
| **Chevrolet** | Silverado 1500 | **709** |
| **Chevrolet** | Silverado 2500HD | **99** |
| **Chevrolet** | Silverado 3500HD | **84** |
| **Chevrolet** | Colorado | **95** |
| **GMC** | Sierra 1500 | **700** |
| **GMC** | Sierra 2500HD | **123** |
| **GMC** | Sierra 3500HD | **87** |
| **GMC** | Canyon | **53** |
| **Toyota** | Tacoma | **193** |
| **Toyota** | Tundra | **119** |
| **Nissan** | Titan | **140** |
| **Nissan** | Frontier | **29** |
| **Total** | **All Supported Makes/Models** | **6,954 Real Alberta Records** |

---

## 3. Data Scope Filters & Provenance Tracking

1. **Database Source Tagging:**
   - Source 1 (`synthetic_simulator_demo`): Type `manual_import` (56 records)
   - Source 2 (`ca-dealers-used-2022`): Type `open_data` (6,954 records)
2. **FastAPI Endpoints (`services/api/carvalue_api/__init__.py`):**
   - `GET /v1/system/status`: Returns `sources_breakdown` separating real vs synthetic counts.
   - `POST /v1/valuations`: Accepts `dataset_filter: "real_only" | "all" | "synthetic_only"`. Returns `dataset_provenance`, `real_comparables_count`, and `synthetic_comparables_count`.
3. **Web UI (`apps/web/`):**
   - Added interactive 3-way toggle button on the valuation form: `🟢 Real Dealer (2022)` *(Default)*, `📊 All Sources`, `🧪 Simulated Only`.
   - Result card dynamically displays the provenance badge and comparable breakdown.

---

## 4. Price Aging & Macro Drift Economics

To answer how 2022 historical listings predict 2026 asking prices, the valuation engine separates two distinct phenomena:

1. **Vehicle Age Depreciation (Micro Dynamic):**
   $$\text{Vehicle Age at Valuation} = \text{Valuation Year (2026)} - \text{Model Year}$$
   A 2021 F-150 evaluated in 2026 has an age of 5 years. The model evaluates the 5-year depreciation point rather than anchoring to the 2022 observation year.
2. **Macro Price Drift & Inflation (Macro Dynamic):**
   $$\text{Adjusted Price} = \text{Base Estimate} \times (1 + r_{\text{annual}})^{\Delta t}$$
   Where $r_{\text{annual}}$ is the configurable annual used-vehicle price index drift rate (tunable in the Admin ML Studio, default 2.5%/year).

---

## 5. Admin Portal & ML Studio (`/admin`)

Created a dedicated Admin & ML Studio page ([`apps/web/src/app/admin/page.tsx`](file:///mnt/e/projects/CarValue/apps/web/src/app/admin/page.tsx)):
- **Authentication:** Configured default user `admin` / `admin12345`.
- **Tabs:**
  1. 📊 **Live Overview:** Total listings, comps, model health, freshness metrics.
  2. 🗃️ **Datasets & Sources:** Source permission gates, approved vs denied feeds.
  3. 🤖 **ML Studio & Model Tuning:** Algorithm candidates (OLS Baseline, CatBoost, Ridge), macro drift rate slider, refusal threshold inputs, model version registry with 1-click **Promote to ACTIVE**.
  4. 🛡️ **Audit Trail:** Real-time stream of valuation events, latency, and confidence ratings.

---

## 6. Layout Modernization & ResoLogix Footer

1. **Header Restructuring ([`layout.tsx`](file:///mnt/e/projects/CarValue/apps/web/src/app/layout.tsx)):**
   - Brand logo + `CarValue™` + `v1.2.2` badge.
   - Cleaned navigation with direct links to **`Docs`** (`/docs`) and **`Admin`** (`/admin`).
2. **Dedicated Documentation ([`docs/page.tsx`](file:///mnt/e/projects/CarValue/apps/web/src/app/docs/page.tsx)):**
   - Explains statistical prediction intervals, price aging formulas, FOIP/PIPA privacy guardrails, and API contracts.
3. **Footer Styling (Matching `resologix.alfazen.org`):**
   - Left: *Disclaimer* (modal) | *Data Rights & Privacy* | *Docs*
   - Center: *CarValue™ Vehicle Intelligence* | *© 2026 Alfazen Inc. All rights reserved*
   - Right: Social & contact icons (Mail, Web, X/Twitter, LinkedIn).

---

## 7. Unified Single Port 4020 Architecture

Standardized the entire development and production interface on a single entry point:

```text
               User Browser / Client
                         │
                         ▼
        ┌──────────────────────────────────┐
        │       Unified Port: 4020         │
        │     (Next.js App & Proxy)        │
        └────────────────┬─────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │ (Internal Next.js Rewrites)   │
         ▼                               ▼
  Frontend Pages                   FastAPI Backend
  (/, /docs, /admin, /privacy)    (Internal :8000)
                                  (/api/v1/*, /api/admin/*)
```

### Verification Across Port 4020
```bash
  200 OK: http://localhost:4020/
  200 OK: http://localhost:4020/docs
  200 OK: http://localhost:4020/admin
  200 OK: http://localhost:4020/privacy
  200 OK: http://localhost:4020/api/v1/system/status
  200 OK: http://localhost:4020/api/v1/taxonomy
```

---

## 8. Git Revision History

- **Repository:** `https://github.com/marcuz-apl/carvalue.git`
- **Branch:** `master`
- **Key Commits:**
  - `217e353`: Real dealer ingestion, provenance tracking, and data scope filters.
  - `2ce192b`: Admin ML Studio, Docs page, header restructuring, and ResoLogix footer.
  - `6580936`: Single port 4020 standardization across `package.json` and testing guides.
