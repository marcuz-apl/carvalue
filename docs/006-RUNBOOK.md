# Operator Runbook: CarValue Alberta Valuator

**Scope:** Deployment, model training & promotion, crawler operations, database maintenance, and disaster recovery.

---

## 1. System Setup & Initial Deployment

### A. Environment Initialization
```bash
# 1. Initialize project virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Initialize SQLite Database & System of Record
./bin/carvalue init-db --db-url "sqlite:///./carvalue.db"

# 3. Start API Service
./bin/carvalue run --host 0.0.0.0 --port 8000 --db-url "sqlite:///./carvalue.db"
```

### B. Frontend Deployment (`apps/web`)
```bash
cd apps/web
npm install
npm run build
npm run start
```

---

## 2. Model Lifecycle & Governance Operations

### A. Training Offline Model Candidates
1. Query training dataset snapshot from active `ListingPriceHistory`.
2. Fit `OLSBaseline` and `CatBoostCandidate` across chronological split.
3. Compute metrics (MAE in CAD, MdAPE, RMSE, 80% coverage, segment slices).
4. Save artifact to versioned path (e.g. `models/catboost_20260824.joblib`).
5. Register model row in `ModelVersion` table with status `"candidate"`.

### B. Explicit Model Promotion
Model training completion **never** automatically activates a model. To promote:
```bash
# Authenticate to Admin API
curl -X POST http://localhost:8000/admin/models/{model_id}/promote \
  -H "X-CSRF-Token: <csrf_token>" \
  --cookie "carvalue_admin_session=<session_token>"
```
*Effect:* Target model becomes `active`, previous active model is marked `retired`, and an `AuditEvent` is appended.

### C. Instant Rollback Procedure
If live monitoring detects valuation anomalies or regressions:
```bash
curl -X POST http://localhost:8000/admin/models/{previous_model_id}/rollback \
  -H "X-CSRF-Token: <csrf_token>" \
  --cookie "carvalue_admin_session=<session_token>"
```

---

## 3. Disaster Recovery & Maintenance Runbook

### A. Point-in-Time Database Backup
```bash
# Run online SQLite snapshot with WAL consistency
carvalue backup-db --db-url "sqlite:///./carvalue.db" --dest "/backups/carvalue_$(date +%Y%m%d_%H%M%S).db"
```

### B. Database Restoration Drill
```bash
# Validate checksum and restore SQLite database
carvalue restore-db --src "/backups/carvalue_20260824_120000.db" --db-url "sqlite:///./carvalue.db"
```

### C. Scheduled Data Retention Purge
```bash
# Purge raw observations > 90 days and expired sessions > 30 days
carvalue purge-retention --db-url "sqlite:///./carvalue.db" --raw-days 90 --session-days 30
```

---

## 4. Operational Monitoring & Health Checks

- **API Status & Freshness:** `GET /v1/system/status`
  - Alert threshold: `data_freshness_days > 14` triggers a crawler freshness warning.
  - Alert threshold: `active_model == null` triggers an unconfigured model alert.
- **Health Check Probe:** `GET /healthz` (returns HTTP 200 `{"ok": true}`).
- **Audit Logs:** `GET /admin/audit` (inspect recent administrative mutations).
