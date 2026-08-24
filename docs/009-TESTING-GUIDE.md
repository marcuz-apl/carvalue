# CarValue Testing Guide

A comprehensive guide for testing the CarValue platform: automated test suites, local full-stack execution, interactive browser user journeys, Swagger API verification, and CLI maintenance commands.

---

## 1. Automated Test Suites (pytest)

Run the full automated test suite (84 unit and integration tests across M0–M8):

```bash
/home/zenusr/.venv_carvalue/bin/pytest -v
```

### Focused Milestone Test Commands

| Milestone | Command | What It Verifies |
|:---|:---|:---|
| **Full Suite** | `pytest -v` | All 84 unit and integration tests across the modular monolith. |
| **M6 (Web App)** | `pytest tests/test_web_contract.py -v` | Next.js app structure, public visitor contract, 80% interval outputs, zero-auth guarantees. |
| **M7 (Hardening)** | `pytest tests/test_launch_hardening.py -v` | Security headers (`nosniff`, `DENY` framing, CSP), system status endpoint, SQLite online backup/restore, retention purging. |
| **M8 (Expansion)** | `pytest tests/test_coverage_expansion.py -v` | Heavy-Duty pickup taxonomy resolution, Alberta regions, segment regression gates, anonymous feedback API. |
| **M5 (Admin & Worker)** | `pytest tests/test_admin_security.py tests/test_admin_api.py tests/test_worker_engine.py -v` | PBKDF2 password hashing, CSRF protection, 12h session tokens, crawler preflights, batch runner. |
| **M3 (Valuation ML)** | `pytest tests/test_valuation_models.py -v` | Centered-age `OLSBaseline`, `CatBoostCandidate`, 80% prediction intervals, chronological splits, refusal rules. |
| **M1 & M2 (Ingestion)** | `pytest tests/test_spreadsheet_import.py tests/test_import_data_quality.py -v` | Spreadsheet dry-run preview/commit, observation deduplication, price history appending. |
| **M0 (Database)** | `pytest tests/test_migrations.py tests/test_cli_init_db.py -v` | SQLite migration runner, schema versioning, taxonomy and admin user seeding. |

---

## 2. Full-Stack Local Execution & Browser Testing

To test the entire web application and backend interactively in your browser:

### Step 1: Initialize Database & Seed Alberta Taxonomy
```bash
/home/zenusr/.venv_carvalue/bin/carvalue init-db --db-url "sqlite:///./carvalue.db"
```

### Step 2: Start the FastAPI Backend Server
```bash
/home/zenusr/.venv_carvalue/bin/carvalue run --host 127.0.0.1 --port 8000 --db-url "sqlite:///./carvalue.db"
```

### Step 3: Start the Next.js Frontend Development Server
In a second terminal:
```bash
cd apps/web
npm run dev
```

### Step 4: Test Visitor Journeys in Your Browser (`http://localhost:3000`)

1. **Happy Path Valuation:**
   - Select **Make:** `Ford` $\rightarrow$ **Model:** `Ranger` $\rightarrow$ **Year:** `2022` $\rightarrow$ **Trim:** `XLT`.
   - Enter **Odometer:** `45,000 km` $\rightarrow$ Select `4WD` $\rightarrow$ Click **"Get Asking-Price Estimate"**.
   - **Expected Result:** Displays asking price in CAD (rounded to nearest $100), 80% prediction interval gradient bar (`$XX,XXX – $XX,XXX CAD`), confidence badge, Alberta comparables count, data freshness pill, and mandatory legal disclaimer.

2. **Benchmark Preset Cards:**
   - Scroll to **"Alberta Pickup Benchmarks"** and click on *2021 Ford F-150 Lariat 4x4* or *2020 Chevrolet Silverado 1500 LT*.
   - **Expected Result:** Form auto-fills and triggers instant valuation.

3. **Explainable Refusal ("Insufficient Data"):**
   - Select an out-of-distribution mileage (e.g. `650,000 km`) or an unsupported vehicle configuration.
   - **Expected Result:** Displays the **Refusal Card** explaining why precision was not fabricated without guessing.

4. **Anonymous Feedback Widget:**
   - Click 👍 (Yes) or 👎 (No) below any estimate result.
   - **Expected Result:** Button state updates and transmits rating to `/v1/valuations/feedback` without collecting visitor identity.

5. **Methodology & Privacy Pages:**
   - Click **"Methodology"** ([`http://localhost:3000/methodology`](http://localhost:3000/methodology)) to review centered-age baseline models, CatBoost quantile regressions, and governance rules.
   - Click **"Privacy"** ([`http://localhost:3000/privacy`](http://localhost:3000/privacy)) to review zero-PII policies under Alberta PIPA and Canadian PIPEDA.

---

## 3. Interactive API Documentation (Swagger / OpenAPI)

When the backend server is running, navigate to:  
👉 **`http://127.0.0.1:8000/docs`**

Test backend endpoints interactively:
- **`GET /v1/system/status`**: View operational health, active model algorithm & training timestamp, and market data freshness.
- **`GET /v1/taxonomy`**: Inspect supported Alberta pickup makes, models, and trim packages.
- **`POST /v1/valuations`**: Execute asking-price valuation requests via JSON payload.
- **`POST /v1/valuations/feedback`**: Submit anonymous feedback events.
- **`POST /admin/login`**: Authenticate operator admin (`admin@carvalue.local` / `CarValueAdmin2026!`).

---

## 4. CLI Maintenance Operations

Test maintenance and disaster recovery tools directly via the command-line:

```bash
# 1. Take a point-in-time database snapshot (SQLite Online Backup API)
carvalue backup-db --db-url "sqlite:///./carvalue.db" --dest "./backups/test_backup.db"

# 2. Test database restoration drill
carvalue restore-db --src "./backups/test_backup.db" --db-url "sqlite:///./restored_test.db"

# 3. Test scheduled retention purge (raw observations >90d, expired sessions >30d)
carvalue purge-retention --db-url "sqlite:///./carvalue.db" --raw-days 90 --session-days 30
```
