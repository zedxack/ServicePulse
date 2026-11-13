# ServicePulse Testing Strategy & Test Suite Guide

**Author:** Muhammadyusuf Usmonov  
**Project:** ServicePulse (AT-Servis BMI)  
**Version:** 3.0.0  

---

## 1. Overview & Test Philosophy

The ServicePulse test suite is engineered for zero-compromise security, multi-tenant isolation, and reliable asynchronous execution. It guarantees:
- **100% Passing Baseline:** All 47 tests execute cleanly with zero errors in both Docker (PostgreSQL 16) and Windows local environments.
- **Cross-Tenant Security:** Automated adversarial tests verify that no tenant can enumerate, read, update, or delete another tenant's resources.
- **Asynchronous Protocol Integrity:** Background scheduler concurrency, network probe timeouts, and agent command transitions are validated.

---

## 2. Test Execution Commands

### In Docker Container (PostgreSQL 16)
```bash
# Full test suite
docker compose exec backend pytest

# Verbose output with timing
docker compose exec backend pytest -v

# Run Step 3 monitoring and remediation tests only
docker compose exec backend pytest backend/tests/test_step3_network_monitoring.py backend/tests/test_step3_incident_and_recovery.py backend/tests/test_step3_remediation_engine.py backend/tests/test_step3_historical_uptime.py

# Lint check
docker compose exec backend ruff check backend
```

### In Local Windows Environment
```powershell
# Run with virtual environment pytest
.\.venv\Scripts\pytest -v

# Local ruff lint check
.\.venv\Scripts\ruff check backend
```

---

## 3. Test Suite Breakdown (47 Tests Total)

| Test Module | Test Count | Focus Area |
|---|---|---|
| `test_agent_api.py` | 2 | Agent enrollment, heartbeat, telemetry ingestion |
| `test_auth_api.py` | 6 | Argon2id login, refresh rotation, RBAC role assignment |
| `test_dashboard_api.py` | 2 | Role-based dashboard responses, platform vs sysadmin |
| `test_db_and_models.py` | 4 | SQLAlchemy ORM relationships, foreign key integrity |
| `test_health.py` | 3 | Container health endpoints (`/health`, `/api/v1/health`) |
| `test_helpdesk_and_software_api.py` | 2 | Ticket workflows, comments, software request approvals |
| `test_incident_api.py` | 2 | Incident lifecycle, active deduplication key handling |
| `test_inventory_api.py` | 4 | Building, floor, room, device hierarchy |
| `test_multi_tenant_api.py` | 4 | Tenant isolation on core resources |
| `test_security.py` | 4 | Password complexity, token expiration, anti-enumeration |
| `test_step2_security_audit.py` | 6 | Full cross-tenant isolation on all 8 resources & parent ownership |
| `test_step3_historical_uptime.py` | 1 | Duration-based uptime, maintenance window exclusion, sparse data handling |
| `test_step3_incident_and_recovery.py` | 1 | Consecutive failure thresholds, warning/offline states, auto-recovery |
| `test_step3_network_monitoring.py` | 3 | Worker health, on-demand probes, status and maintenance endpoints |
| `test_step3_remediation_engine.py` | 3 | Action allowlist validation, approval workflow, simulation progress |

---

## 4. Database Fixtures & Concurrency Management

- **Isolated Sessions:** All API tests utilize the `client: AsyncClient` and `test_db: AsyncSession` fixtures defined in `backend/tests/conftest.py`.
- **Timezone Awareness:** All datetime logic uses UTC with explicit timezone handling (`_ensure_utc`), guaranteeing identical behavior across SQLite and PostgreSQL.
- **Deterministic Adapters:** Simulated probe tests use the simulation adapter with predictable latency, avoiding live network flakiness.
