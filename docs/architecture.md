# ServicePulse Architecture Specification

**Author:** Muhammadyusuf Usmonov  
**Academic Purpose:** AT-Servis BMI  
**Version:** 1.0.0

---

## 1. System Overview

ServicePulse is structured around an autonomous, closed-loop operational lifecycle:

```
+-----------+      +------------+      +------------+      +------------+
|  MONITOR  | ---> |   DETECT   | ---> |  ANALYZE   | ---> |  CLASSIFY  |
+-----------+      +------------+      +------------+      +------------+
                                                                 |
+-----------+      +------------+      +------------+            v
|  RECORD   | <--- |   VERIFY   | <--- |  RESPOND   | <----------+
+-----------+      +------------+      +------------+
```

1. **MONITOR:** Periodic ICMP echo requests, TCP port probes (e.g. 80, 443, 554 RTSP, 8291 WinBox), and native Windows Agent telemetry heartbeats.
2. **DETECT:** Network timeout, port connection failure, or abnormal system metrics (CPU > 90%, RAM > 95%, disk > 90%, offline heartbeat).
3. **ANALYZE:** Evaluation against threshold policies (e.g. 3 consecutive failed checks).
4. **CLASSIFY:** Deduplication fingerprint calculation (`SHA256(device_id + check_type + port)`) to associate repeated events with the active incident or generate a new incident with severity (`critical`, `warning`, `info`).
5. **RESPOND:** Matching against allowlisted automated remediation rules. If sensitive, queues for administrator approval; if pre-approved, dispatches command.
6. **VERIFY:** Independent probe (re-pinging gateway, querying service status, or verifying socket response) to validate recovery.
7. **RECORD:** Permanent, append-only audit trail and incident event log for post-mortem analysis and SLA calculation.

---

## 2. Monorepo Organization

- `backend/`: FastAPI async service, SQLAlchemy 2.0 ORM, Pydantic v2 validation, Argon2id security.
- `agent/`: Standalone Python agent for Windows endpoints with local SQLite persistence and retry.
- `frontend/`: React 19 + TypeScript + Vite + Tailwind CSS dashboard.
- `infra/`: Docker, Caddy, Nginx proxy, and SSL configurations.
- `docs/`: System documentation, API guides, and BMI defense research notes.

---

## 3. Security Boundary & Least Privilege

- **Zero Arbitrary Execution:** No arbitrary shell commands or raw scripts can be submitted via API. Only strictly allowlisted action codes (`restart_service`, `check_network`, `restart_agent`) with validated parameters are allowed.
- **Argon2id Password Hashing:** Industry-standard password hashing using `argon2-cffi` with 64 MB memory cost, 3 iterations, and 4 threads.
- **Cryptographic Audit Log:** All administrative operations and automated actions are logged to an append-only table `audit_logs` containing actor, target, timestamp, IP, and status.
