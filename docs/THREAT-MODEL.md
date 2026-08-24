# Threat Model: CarValue Alberta Valuator

**Document Version:** 1.0.0  
**Effective Date:** August 2026  
**Scope:** Public web application, FastAPI valuation services, background ingestion worker, SQLite persistence, and ML model registry.

---

## 1. System Architecture & Assets

CarValue is a modular monolith operating on SQLite (WAL mode) designed to deliver explainable asking-price estimates for Alberta pickup trucks.

### Core Assets:
1. **Model Registry & Valuation Integrity:** Prediction intervals, model artifacts (`.joblib`), calibration parameters, and promotion audit logs.
2. **Persistence Store:** Normalized vehicle listings, price history, deduplication fingerprints, and source provenance.
3. **Admin Surface:** Operator credentials, session tokens, audit trail events, and source policy toggles.
4. **Data Acquisition Pipeline:** Source rate limiters, robots.txt preflight checks, and source permission boundaries.

---

## 2. Threat Analysis by Surface

### A. Public Visitor Surface (Internet $\rightarrow$ `/v1/valuations`)

| Threat ID | Description | Impact | Mitigations in Place |
|:---|:---|:---|:---|
| **T-PUB-01** | Denial of Service / Heavy Query Flooding | API latency degradation | Lifespan in-memory SQLite indexing; sub-50ms inference latency; rate limiting and connection timeouts. |
| **T-PUB-02** | Adversarial Out-of-Distribution Inputs (e.g. 5,000,000 km odometer, negative years) | Fabricated / nonsensical price predictions | Pydantic boundary validation (`year` 2010–2035, `mileage_km` $\ge 0$); `evaluate_prediction()` refusal policy returning zeroed estimate and `insufficient_data`. |
| **T-PUB-03** | Scraping / Valuation Extraction Harvesting | Commercial data harvesting | No public batch endpoint; visitor telemetry logging (`ValuationEvent`); single-vehicle valuation constraints. |
| **T-PUB-04** | Visitor Privacy & Tracking Abuse | Regulatory non-compliance (PIPA/PIPEDA) | Zero visitor accounts, zero email/phone collection, coarse UA classification only, no IP address storage in product analytics. |

---

## 3. B. Admin Surface (Internet $\rightarrow$ `/admin/*`)

| Threat ID | Description | Impact | Mitigations in Place |
|:---|:---|:---|:---|
| **T-ADM-01** | Session Hijacking & Credential Sniffing | Unauthorized admin access | PBKDF2-HMAC-SHA256 password hashing (100,000 iterations); 12-hour session expiry; `HttpOnly`, `SameSite=Lax`, `Secure` cookies. |
| **T-ADM-02** | Cross-Site Request Forgery (CSRF) | Forged state mutations (e.g. model rollback, source toggle) | Cryptographically random CSRF tokens validated on all mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) via `require_csrf`. |
| **T-ADM-03** | Unauthorized Model Promotion / Rollback | Regressed or poisoned valuation model in production | Authenticated admin dependency; mandatory `AuditEvent` logging with actor email and SHA256 model checksum. |
| **T-ADM-04** | Clickjacking / Content Framing | UI manipulation | `X-Frame-Options: DENY` and `Content-Security-Policy: default-src 'self'` injected by middleware. |

---

## 4. C. Data Ingestion & Worker Pipeline

| Threat ID | Description | Impact | Mitigations in Place |
|:---|:---|:---|:---|
| **T-ING-01** | Unauthorized Ingestion of Non-Approved Source | Legal liability & source rights violation | Deny-by-default preflight (`SourcePreflightChecker`): fails closed unless `permission_status == 'approved'`, review age $\le 90$ days, and `enabled == True`. |
| **T-ING-02** | Malicious Spreadsheet Payloads (Formula Injection) | Server or analyst compromise | Cells evaluated strictly as raw string/numeric literals; zero formula execution (`test_spreadsheet_import.py`). |
| **T-ING-03** | Double Crawl / Concurrent Lock Contention | Database locking & duplicate records | Exclusive database-backed leases (`SourceLeaseManager` via `CrawlRun` unique index constraint `uq_crawl_runs_active_per_source`). |
| **T-ING-04** | Ingestion of PII (Seller Names, Phone Numbers, Photos) | Privacy violation | Normalized observation schema stores vehicle attributes only (`ListingObservation`); raw fields stripped before persistence. |

---

## 5. Security Summary & Launch Readiness

- **Authentication:** Session tokens hashed with SHA256 in database; zero plaintext credential storage.
- **Audit Logging:** Tamper-evident append-only `audit_events` table tracking all administrative mutations.
- **Fail-Closed Architecture:** Refusal on sparse/OOD inputs; crawler stop on unapproved source permissions.
