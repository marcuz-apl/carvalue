# 011: Temporal Devaluation & Multi-Year Asking-Price Projection

**Date**: 2026-08-25  
**Component**: ML Engine (`carvalue_core.models`), Ingestion Pipeline, API Valuation Service (`carvalue_api`)  
**Status**: Production / Verified

---

## 1. Dataset Origin & Provenance Record

* **Source**: [MarketCheck Automotive Data (US & Canada) on Kaggle](https://www.kaggle.com/datasets/rupeshraundal/marketcheck-automotive-data-us-canada)
* **Dataset Scope**: Real Canadian dealer used inventory listings (2022 historical cohort).
* **Ingestion Tag**: `ca-dealers-used-2022`
* **Observations Ingested**: 44,420 valid Alberta and Canadian pickup truck listings across Ford, Chevrolet, GMC, Ram, and Toyota.

---

## 2. Problem: Historical Baseline vs. Present-Day Valuations

When training on historical inventory datasets (such as 2022 listings), calculating vehicle age relative to runtime `today()` produces a critical temporal anchor flaw:
- A 2021 Ford Ranger listed in 2022 was **1.0 year old** at an asking price of **$39,300 CAD**.
- If training calculates vehicle age as `2026 - 2021 = 5.0 years`, the model mistakenly learns that a **5-year-old** vehicle is worth $39,300 CAD.
- Consequently, evaluating a 2021 vehicle in 2026 would fail to devalue the vehicle over time.

---

## 3. Solution: Observation-Anchored Age & Learned ML Depreciation

### 3.1 Observation-Anchored Training
During model training (`CatBoostCandidate.fit` and `OLSBaseline.fit`), each record's `vehicle_age` is calculated relative to its exact **observation timestamp** (`observed_at`):
$$\text{Age}_{\text{obs}} = \text{vehicle\_age\_years}(\text{model\_year}, \text{observed\_at})$$

This enables the machine learning model to learn the true empirical depreciation rate $f(\text{Age}, \text{Mileage}, \text{Trim}, \text{Drivetrain}, \text{Make/Model})$.

### 3.2 Evaluation as of Valuation Date
When generating asking-price estimates as of the valuation date $t_{\text{val}}$ (e.g. August 2026):
$$\text{Age}_{\text{val}} = \text{vehicle\_age\_years}(\text{model\_year}, t_{\text{val}})$$

For a 2021 Ford Ranger XLT 4WD with 77,000 km:
* **In 2022 (Age ~1.0 yr)**: Predicted asking price = **CAD $40,451**
* **In August 2026 (Age ~5.15 yrs)**: Projected asking price = **CAD $31,161 – $36,700** (devalued by -$9,100 CAD or ~20% along the learned depreciation curve).

---

## 4. Verification & Status

* `CatBoostCandidate` trained and registered as the active production model artifact in SQLite.
* Unit and integration test suite (`tests/`) passes 84/84 tests.
