# Privacy & Data Rights Review: Alberta & Canadian Obligations

**Statutory Framework:** Alberta Personal Information Protection Act (PIPA) & Canadian PIPEDA  
**Applicable Scope:** Public web experience, valuation inference engine, telemetry logging, and data ingestion.  
**Review Status:** Approved for MVP Launch  

---

## 1. Executive Summary

CarValue is designed from first principles with **privacy-by-default** and **data minimization**. Unlike commercial automotive platforms that capture visitor phone numbers and emails as lead generation, CarValue requires **zero personal identity** to generate asking-price estimates.

---

## 2. Visitor Privacy Compliance

### A. Zero Identity Requirement (PRD Section 10)
- Visitors can view, search, and calculate vehicle valuations completely anonymously.
- No sign-up, registration, email address, phone number, physical address, or IP logging is required or collected.
- No third-party ad networks, tracking pixels (e.g. Meta Pixel, Google Remarketing), or device fingerprinting scripts are present in the frontend.

### B. Telemetry Minimization (`ValuationEvent`)
- Telemetry events capture:
  - Timestamp (UTC).
  - Coarse device category (`mobile` vs `desktop` derived from User-Agent without storing raw User-Agent).
  - Query parameters (vehicle make, model, year, mileage, trim, drivetrain).
  - Model version reference & response latency in milliseconds.
  - User feedback (`useful: true/false`).
- Telemetry **strictly excludes**:
  - Visitor IP addresses.
  - Browser canvas / hardware fingerprints.
  - Geolocation coordinates.

---

## 3. Data Acquisition & Source Privacy

### A. Deny-by-Default Collection
- Automated ingestion is disabled by default (`SourcePolicy.permission_status == 'unknown'`).
- Collection only runs against approved dealer feeds, licensed datasets, or explicit CSV/XLSX imports.
- Platforms without explicit written permission or open licenses (e.g., AutoTrader.ca, CarGurus) are **denied by default**.

### B. Personal Data Stripping at Boundary
- Ingestion adapters extract vehicle specifications only (`make`, `model`, `year`, `mileage_km`, `trim`, `asking_price_cad_cents`).
- Ingestion **never extracts or stores**:
  - Private seller names or dealer salesperson names.
  - Telephone numbers or email addresses.
  - Vehicle photos containing license plates or faces.
  - Seller free-text descriptions containing personal anecdotes.

---

## 4. Retention & Deletion Schedule

| Data Category | Retention Limit | Purge Mechanism |
|:---|:---|:---|
| **Raw Crawl Observations** (`raw_observations`) | 90 Days | Automated purge via `carvalue purge-retention --raw-days 90` |
| **Admin Sessions** (`admin_sessions`) | 30 Days after expiry / revocation | Automated purge via `carvalue purge-retention --session-days 30` |
| **Normalized Price History** (`listing_price_history`) | Indefinite (Non-Personal) | Retained for chronological ML training & market trend analysis |
| **Audit Mutation Trail** (`audit_events`) | 365 Days | Retained for operational security & audit compliance |

---

## 5. Privacy Review Sign-off

The CarValue architecture satisfies Canadian privacy obligations under PIPA/PIPEDA. No personal data processing risks exist for public visitors.
