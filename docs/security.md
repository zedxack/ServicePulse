# ServicePulse Security & Compliance Specification

**Author:** Muhammadyusuf Usmonov  
**Version:** 2.0.0  
**Academic Purpose:** AT-Servis BMI

---

## 1. Multi-Tenant Data Isolation

- **Query-Level Scoping:** All database queries for organization-owned resources (`devices`, `incidents`, `tickets`, `software_requests`, `users`, `buildings`, `audit_logs`) enforce tenant boundary filtering via `scoped_org_id`.
- **Anti-Enumeration Safeguards:** Attempting to query an object belonging to another organization yields a strict `404 Not Found` response instead of `403 Forbidden`, preventing malicious callers from discovering valid IDs across organizations.
- **Tenant Admin Constraints:** Company administrators cannot reassign users or resources to other organizations, cannot create superusers, and cannot assign platform administrative privileges.
- **Platform Super Admin Auditing:** All cross-tenant administrative operations executed by platform administrators are recorded in the append-only `audit_logs` table.

---

## 2. Authentication & Credential Security

- **Argon2id Password Hashing:** User passwords are encrypted using `Argon2id` (memory cost 64 MB, 3 time iterations, 4 parallelism lanes). Raw passwords are never persisted or logged.
- **JWT Architecture:** Access tokens (HS256) have a 60-minute lifetime and encode standard claims (`sub`, `exp`, `iat`, `roles`, `permissions`, `organization_id`, `primary_dashboard`).
- **Single-Use Refresh Token Rotation:** Refresh tokens are tracked in `refresh_tokens` by unique cryptographic identifier (`jti`). Every refresh operation revokes the previous token and issues a new pair, detecting replay attacks.
- **Agent Token Security:** Monitoring agents authenticate via high-entropy pre-shared tokens (`sp_tok_*`). The backend stores only `SHA-256` hashes in `agents.api_token_hash`.

---

## 3. Remote Execution Safety & Zero Arbitrary Script Execution

- **Strict Allowlisting:** Remote agents and backend workers reject arbitrary shell scripts or PowerShell commands.
- **Pre-Approved Remediation Actions:** Only rigidly defined action codes are recognized:
  - `restart_service` (with validated `service_name`)
  - `check_network` (with target IP/hostname)
  - `restart_agent`
  - `install_approved_software` (triggered exclusively through approved software requests)
- **Two-Man Rule (Approval Gating):** Actions marked with `requires_approval=True` cannot execute automatically; they enter a `pending_approval` state requiring explicit confirmation by an authorized administrator.

---

## 4. Audit Logging & Non-Repudiation

- **Append-Only Event Store:** The `audit_logs` table records every critical security action (`auth_login_success`, `auth_login_failed`, `auth_logout`, `user_created`, `user_updated`, `device_created`, `remediation_executed`, etc.).
- **Incident Audit Trail:** Every incident lifecycle state transition (`detected`, `deduplicated`, `assigned`, `acknowledged`, `resolved`) creates an immutable `IncidentEvent` log referencing the timestamp and responsible operator.
