# Technote: Fix for `SourcePolicy` Import Error in Test Collection

**Date:** 2026-08-24  
**Author:** Antigravity / Engineering  
**Scope:** `services/api/carvalue_api/maintenance.py`, `tests/test_launch_hardening.py`  
**Status:** Resolved & Verified  

---

## 1. Issue Description

During pytest test execution (`pytest -v`), test collection failed with an `ImportError`:

```text
============================ ERRORS ============================
_______ ERROR collecting tests/test_launch_hardening.py ________
ImportError while importing test module '/mnt/e/projects/CarValue/tests/test_launch_hardening.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_launch_hardening.py:12: in <module>
    from carvalue_api.maintenance import (
services/api/carvalue_api/maintenance.py:23: in <module>
    from carvalue_core.persistence import (
E   ImportError: cannot import name 'SourcePolicy' from 'carvalue_core.persistence' (/mnt/e/projects/CarValue/packages/core/carvalue_core/persistence.py)
```

---

## 2. Root Cause Analysis

- In `carvalue_core.persistence`, the database model representing data sources and their licensing/preflight policies is named `Source` (which includes columns `permission_status`, `policy_review_date`, `allowed_fields_json`, `rate_limit_per_minute`, etc.).
- When scaffolding `services/api/carvalue_api/maintenance.py` during Milestone M7, `SourcePolicy` was erroneously listed in the `from carvalue_core.persistence import (...)` statement, even though `maintenance.py` only referenced `RawObservation`, `AdminSession`, and `AuditEvent` for retention purging.

---

## 3. Resolution

1. **Removed Extraneous Import:**  
   In `services/api/carvalue_api/maintenance.py`, removed `SourcePolicy` from the import list:
   ```python
   # Before
   from carvalue_core.persistence import (
       AdminSession,
       AuditEvent,
       DatasetSnapshot,
       Listing,
       ListingPriceHistory,
       ModelVersion,
       RawObservation,
       Source,
       SourcePolicy,
   )

   # After
   from carvalue_core.persistence import (
       AdminSession,
       AuditEvent,
       DatasetSnapshot,
       Listing,
       ListingPriceHistory,
       ModelVersion,
       RawObservation,
       Source,
   )
   ```

2. **Verification:**  
   Ran pytest test suite collection to ensure all 80+ tests across M0–M8 collect and execute cleanly.
