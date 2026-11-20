# ServicePulse

**Enterprise Remote Monitoring, Management (RMM) & IT Service Management (ITSM) Platform**

Author: **Muhammadyusuf Usmonov**  
Target Market: **Enterprise IT Operations & Managed Service Providers**  
Official Workspace: `C:\Projects\ServicePulse`

---

## 1. Project Mission

ServicePulse is a remote monitoring, management, and ITSM automation platform engineered for enterprise IT infrastructure. The platform monitors multi-tier organizational assets, detects outages and performance degradations, concurrency-safely deduplicates incidents, triggers allowlisted automated remediation actions, verifies the remediation outcome independently, and provides dual-mode centralized dashboards (Technical Operations for SysAdmins & SLA/Business Impact for Executives).

### Core Operational Lifecycle:
```
MONITOR ➔ DETECT ➔ ANALYZE ➔ CLASSIFY ➔ RESPOND ➔ VERIFY ➔ RECORD
```

---

## 2. Technology Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), PostgreSQL (production) / SQLite aiosqlite (fast local testing), Alembic migrations, Pydantic v2, Argon2id password hashing, PyJWT, pytest, Ruff.
- **Frontend:** React 19, Vite, TypeScript, Tailwind CSS, Lucide React, TanStack Query, i18next (Uzbek, Russian, English), React Hook Form, Zod.
- **Windows Agent:** Native Windows service/process, psutil, WMI, requests, SQLite offline persistent queue, exponential retry with backoff, allowlisted action executor.
- **Infrastructure:** Docker, Docker Compose, PostgreSQL 16, Caddy reverse proxy with automated HTTPS TLS.

---

## 3. Monorepo Repository Structure

```
ServicePulse/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Versioned REST endpoints (health, auth, inventory, incidents, etc.)
│   │   ├── core/            # Configuration, Argon2id security, structured logging
│   │   ├── db/              # SQLAlchemy Base, async session, and database seeding
│   │   ├── models/          # Normalized SQLAlchemy 2.0 ORM models
│   │   ├── schemas/         # Pydantic v2 validation models
│   │   ├── repositories/    # Data access abstraction
│   │   ├── services/        # Business logic services
│   │   ├── workers/         # Background monitoring and remediation workers
│   │   └── main.py          # FastAPI application factory and lifespan hooks
│   ├── migrations/          # Alembic migration scripts and version histories
│   ├── tests/               # Pytest async test suite (11 unit/integration tests)
│   ├── requirements.txt     # Locked production dependencies
│   └── Dockerfile           # Backend container specification
├── agent/                   # Native Windows monitoring and management agent
├── frontend/                # Enterprise React + TypeScript + Tailwind SPA
├── infra/
│   ├── docker/              # Container support configurations (nginx.conf)
│   └── caddy/               # Caddy reverse proxy configuration (Caddyfile)
├── docs/                    # Technical engineering documentation
├── compose.yaml             # Local development orchestration
├── compose.prod.yaml        # Production VPS deployment orchestration
├── pytest.ini               # Pytest test runner configuration
├── .env.example             # Complete environment configuration template
└── README.md
```

---

## 4. Local Development & Quickstart

### Prerequisites
- Windows 11 x64
- Python 3.12+ (Installed in user directory)
- Node.js LTS (v26.13.0+) & npm (v11.20.0+)
- Git for Windows (v2.56.1+)

### Backend Setup & Test Execution
```powershell
# 1. Activate project virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run automated test suite
pytest -v

# 3. Apply database migrations
alembic -c backend/alembic.ini upgrade head

# 4. Seed initial realistic infrastructure (Corporate Headquarters -> Operations Datacenter)
python -m backend.app.db.init_db

# 5. Start development backend server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Endpoints
- Swagger API Docs: `http://localhost:8000/docs`
- ReDoc API Docs: `http://localhost:8000/redoc`
- System Healthcheck: `http://localhost:8000/health`
- Database Probe: `http://localhost:8000/api/v1/health`

---

## 5. Docker Orchestration

- Local development with PostgreSQL container:
  ```bash
  docker compose up -d --build
  ```
- Production VPS deployment:
  ```bash
  docker compose -f compose.prod.yaml up -d --build
  ```

---

## 6. Implementation Status

| Component | Status | Verification |
|---|---|---|
| **Phase 0: Environment Audit & Setup** | **IMPLEMENTED** | Python 3.12, Node.js, npm, Git verified |
| **Phase 1: Backend Foundation & DB Models** | **ACCEPTED** | All 13 ORM models created, Alembic migrations generated and applied |
| **Phase 2: Business Logic & API Layer** | **ACCEPTED** | Multi-tenant RBAC, all 8 cross-tenant isolation endpoints verified (39/39 tests) |
| **Phase 3: Network Monitoring & Remediation** | **ACCEPTED** | Independent worker, SLA calculation, simulation safety, lease lock (61/61 tests) |
| **Phase 4: Native Windows Agent** | **IMPLEMENTED** | Real telemetry, DPAPI vault, offline SQLite queue, safe allowlist, Windows Service, 41/41 tests passing |
| **Phase 5: React Enterprise UI** | *PENDING APPROVAL* | Ready to start upon Step 4 review |
| **Phase 6: End-to-End System Integration** | *PENDING* | Planned |
| **Phase 7: VPS & HTTPS Domain Deployment** | *PENDING* | Prepared (compose.prod.yaml, Caddyfile) |
| **Phase 8: Enterprise Validation & System Metrics**| *PENDING* | Operational benchmark testing documented |
