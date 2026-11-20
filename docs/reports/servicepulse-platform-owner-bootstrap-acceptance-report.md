# ServicePulse — Authoritative Primary Platform Owner Bootstrap & Database Purge Acceptance Report

**Project:** ServicePulse — Enterprise Hybrid RMM & ITSM Platform  
**Branch:** `feature/platform-owner-access-control`  
**Execution Timestamp:** 2026-11-15 22:02:00 UTC+5  
**Authorized Platform Owner:** Muhammadyusuf Usmonov (`muhammadyusufusmonov011@gmail.com`)  
**Database Target:** PostgreSQL 16 Alpine (`servicepulse` database)

---

## 1. Executive Summary

Under explicit authorization from project owner **Muhammadyusuf Usmonov**, a clean database purge and single authoritative owner initialization was executed across the persistent PostgreSQL `servicepulse` database.

All 24 legacy test and demo user accounts have been purged from the system. Exactly **ONE** authoritative user account now exists on the entire platform. Non-nullable relational integrity constraints (`tickets`, `ticket_comments`, `software_requests`) were reassigned to the primary owner without data loss or foreign key violations, and ephemeral session records (`refresh_tokens`, `access_requests`, `organization_invitations`, `user_roles`) were cleared.

Container restart and test suite isolation mechanisms were updated in `backend/app/db/init_db.py`, ensuring that restarting Docker containers preserves this sole owner and never resurrects purged legacy accounts, while automated in-memory test suites (`pytest`, `vitest`) continue to execute with 100% pass rates.

---

## 2. PostgreSQL Live Database State Verification

### 2.1. Sole Authoritative User Account Inspection

```sql
SELECT id, email, full_name, is_active, is_superuser, organization_id FROM users;
```

**Live PostgreSQL Output (Exact 1 Row):**
```text
 id |               email               |       full_name       | is_active | is_superuser | organization_id 
----+-----------------------------------+-----------------------+-----------+--------------+-----------------
 25 | muhammadyusufusmonov011@gmail.com | Muhammadyusuf Usmonov | t         | t            |               1
(1 row)
```

### 2.2. PlatformSettings Singleton Verification

```sql
SELECT id, primary_owner_id, platform_name, allow_public_registration, bootstrap_completed_at FROM platform_settings;
```

**Live PostgreSQL Output:**
```text
 id | primary_owner_id | platform_name | allow_public_registration |    bootstrap_completed_at     
----+------------------+---------------+---------------------------+-------------------------------
  1 |               25 | ServicePulse  | t                         | 2026-11-15 16:54:40.362182+00
(1 row)
```

- `primary_owner_id` (25) references the authoritative owner `muhammadyusufusmonov011@gmail.com`.
- Platform singleton constraint is enforced (`id = 1`).

### 2.3. User Roles Assignment

```sql
SELECT ur.user_id, r.id as role_id, r.name as role_name 
FROM user_roles ur 
JOIN roles r ON ur.role_id = r.id 
WHERE ur.user_id = 25;
```

**Live PostgreSQL Output:**
```text
 user_id | role_id |      role_name       
---------+---------+----------------------
      25 |       4 | platform_super_admin
      25 |       5 | company_admin
      25 |       6 | it_admin
(3 rows)
```

---

## 3. Configuration & Startup Idempotency Hardening

### 3.1. Environment Configuration (`.env` and `compose.yaml`)

`.env`:
```env
FIRST_SUPERUSER_EMAIL="muhammadyusufusmonov011@gmail.com"
FIRST_SUPERUSER_PASSWORD="[REDACTED_PASSWORD]"
```

`compose.yaml` (Backend & Network-Worker environments):
```yaml
FIRST_SUPERUSER_EMAIL: ${FIRST_SUPERUSER_EMAIL:-muhammadyusufusmonov011@gmail.com}
FIRST_SUPERUSER_PASSWORD: ${FIRST_SUPERUSER_PASSWORD:-[REDACTED_PASSWORD]}
```

`backend/app/core/config.py`:
```python
FIRST_SUPERUSER_EMAIL: str = "muhammadyusufusmonov011@gmail.com"
FIRST_SUPERUSER_PASSWORD: str = "[REDACTED_PASSWORD]"
```

### 3.2. Idempotent Initialization Logic (`backend/app/db/init_db.py`)

- Before creating seed accounts, `init_db` executes:
  ```python
  ps_res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
  ps = ps_res.scalar_one_or_none()
  owner_exists = False
  if ps and ps.primary_owner_id:
      owner_res = await db.execute(select(User).where(User.id == ps.primary_owner_id))
      owner = owner_res.scalar_one_or_none()
      if owner and owner.is_active and owner.is_superuser:
          owner_exists = True
  ```
- **Live Persistent Database Behavior:** `owner_exists` evaluates to `True`. `init_db` logs:
  `Authoritative primary platform owner is already established (muhammadyusufusmonov011@gmail.com). Preserving existing users and access governance configuration.`
  All seed account creation is skipped. Container restarts never re-seed or overwrite the owner.
- **Isolated In-Memory Pytest Behavior:** In fresh SQLite databases, `ps` does not yet exist (`owner_exists = False`). Both the authoritative superuser (`muhammadyusufusmonov011@gmail.com`) and legacy test accounts (`admin@servicepulse.uz`, `company_admin@servicepulse.uz`) are seeded, ensuring all tests pass without regression.

---

## 4. Live API Authentication Verification

Live HTTP requests executed against `http://localhost:8000`:

### 4.1. `POST /api/v1/auth/login`
- **Payload:** `{"email": "muhammadyusufusmonov011@gmail.com", "password": "[REDACTED_PASSWORD]"}`
- **HTTP Status:** `200 OK`
- **Response:**
  - `token_type`: `bearer`
  - `access_token`: Valid HS256 JWT (length 1961 bytes)
  - `refresh_token`: Cryptographically secure rotating token with persisted `jti` (length 220 bytes)

### 4.2. `GET /api/v1/auth/me`
- **Headers:** `Authorization: Bearer <access_token>`
- **HTTP Status:** `200 OK`
- **Response Payload:**
  - `id`: `25`
  - `email`: `"muhammadyusufusmonov011@gmail.com"`
  - `full_name`: `"Muhammadyusuf Usmonov"`
  - `is_active`: `true`
  - `is_superuser`: `true`
  - `is_primary_owner`: `true`
  - `organization_id`: `1`
  - `roles`: `["platform_super_admin", "company_admin", "it_admin"]`

### 4.3. `POST /api/v1/auth/refresh`
- **Payload:** `{"refresh_token": "<refresh_token>"}`
- **HTTP Status:** `200 OK`
- **Response:** Successfully rotated access token and persisted new token record.

---

## 5. Automated Regression Test Suite Verification

| Suite | Scope | Total Tests | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Backend Pytest** | Security, RBAC, Multi-Tenant Isolation, RMM & ITSM APIs | 112 | 112 | 0 | **PASS (100%)** |
| **Frontend Vitest** | NOC Shell, Command Palette, RMM Inspector, War Room, Auth | 80 | 80 | 0 | **PASS (100%)** |
| **Live Database State** | Postgres `servicepulse` User Count | 1 | 1 | 0 | **PASS (100%)** |
| **API Endpoints** | Live Login, Profile, and Refresh Token Rotation | 3 | 3 | 0 | **PASS (100%)** |

---

## 6. Audit Sign-Off

All requirements have been met:
1. All 24 legacy accounts safely purged.
2. Authoritative Primary Platform Owner (`muhammadyusufusmonov011@gmail.com`) initialized with Argon2id encryption.
3. Sole owner linked to `platform_settings.primary_owner_id`.
4. Startup idempotency hardened across `.env`, `compose.yaml`, `config.py`, and `init_db.py`.
5. 112/112 backend tests and 80/80 frontend tests passing cleanly.
