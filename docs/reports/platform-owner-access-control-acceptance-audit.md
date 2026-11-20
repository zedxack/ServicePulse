# ServicePulse — Primary Platform Owner Security & Authentication Acceptance Audit Report

**Audit Date:** November 15, 2026  
**Auditor:** Independent Principal Security Engineer & Backend Architect  
**Milestone:** Platform Owner Bootstrap, Authentication Repair & Centralized Access Governance  
**Repository:** ServicePulse (`C:\Projects\ServicePulse`)  
**Target Branch:** `feature/platform-owner-access-control`  
**Baseline Branch:** `feature/servicepulse-design-system`  
**Baseline Commit:** `ece18ab98e551b21b15367fa96c83a48cbee92ff`  
**Inspection Mode:** Strictly Read-Only on Persistent Development Database (`servicepulse`)  

---

## 1. Executive Summary & Audit Decision

### Audit Decision: **CONDITIONAL PASS**
*(Pending remediation of the Critical Session Invalidation / Refresh Token Revocation Defect documented in Section 4)*

An exhaustive, evidence-backed security audit was conducted on branch `feature/platform-owner-access-control`. All components of the Platform Owner Bootstrap and Centralized Access Governance milestone were independently evaluated through live database inspection, direct API interaction, automated penetration testing, and static analysis.

### High-Level Evaluation Matrix

| Domain | Scope | Status | Notes |
| :--- | :--- | :--- | :--- |
| **1. Primary Owner Identity** | PostgreSQL verification of singleton `PlatformSettings` and User #1 | **PASS** | Exactly 1 singleton row, linked to User #1 (`admin@servicepulse.uz`), active, `platform_super_admin`. |
| **2. Target DB Distinction** | Identification of database modified by CLI bootstrap | **PASS** | Target DB is `servicepulse` (dev DB); `servicepulse_test` contains Alembic schema but zero persistent rows. |
| **3. Owner Authentication** | Live API login, JWT structure, profile claims, dashboard access | **PASS** | HTTP 200, JWT claims valid, `is_primary_owner: true`, dashboard access granted. |
| **4. Session Termination** | Token invalidation and session destruction upon logout | **FAIL (CRITICAL)** | Refresh token revocation check in `AuthService.refresh_access_token` bypassed. Logged-out tokens can still mint new access tokens. |
| **5. Authoritative Authorization** | Database-backed owner verification (`require_primary_owner`) | **PASS** | Queries live DB session; rejects non-owner superadmins (403), company admins (403), employees (403), and stale JWTs claiming ownership. |
| **6. Access Governance (7 Types)** | Full lifecycle across all 7 access request categories | **PASS** | 100% verified across org registration, membership, and 5 tenant roles. |
| **7. Anti-Escalation & Isolation** | Privilege escalation, self-approval, tenant boundaries | **PASS** | Non-owners blocked from approving own or others' requests; cross-tenant access blocked (403). |
| **8. Token Rotation & Single Use** | Invitation token rotation and concurrency handling | **PASS** | Single-use invitations invalidated upon redemption; concurrent approvals handled idempotently. |
| **9. Rejection Validation** | Mandatory justification rule (>= 3 chars) and audit trail | **PASS** | Empty or short reasons rejected (422); valid rejections persist reason and emit immutable audit log. |
| **10. Database Isolation** | Dev database integrity vs test database isolation | **PASS** | `servicepulse` records preserved without data corruption; tests run exclusively in `servicepulse_test`. |
| **11. Branding & Metadata** | Scanning UI, locales, seeds, and active screenshots | **PASS** | Zero visible occurrences of `TATU`, `tatu.uz`, `BMI`, or thesis metadata. Historical `*_before.png` untouched. |
| **12. Regression Test Suite** | Backend tests, frontend vitest, Vite build, linters | **PASS** | 32/32 backend tests passed; 57/57 frontend tests passed; Vite build succeeded; ESLint 0 warnings; Ruff clean. |

---

## 2. Exact Primary Owner Verification

Direct SQL inspection of the persistent PostgreSQL development database (`servicepulse`) verified the exact identity and governance configuration:

### 2.1. `platform_settings` Singleton Inspection
```sql
SELECT id, platform_name, primary_owner_id, allow_public_registration, bootstrap_completed_at
FROM platform_settings;
```
* **Result:** Exactly 1 row.
* `id`: `1`
* `platform_name`: `'ServicePulse'`
* `primary_owner_id`: `1`
* `allow_public_registration`: `true`
* `bootstrap_completed_at`: `2026-11-15 08:07:50.761686+00`

### 2.2. User ID 1 Account Attributes
```sql
SELECT id, email, full_name, is_active, is_superuser, organization_id
FROM users WHERE id = 1;
```
* `id`: `1`
* `email`: `admin@servicepulse.uz`
* `full_name`: `'Primary Platform Owner'`
* `is_active`: `true`
* `is_superuser`: `true`
* `organization_id`: `1` (Example Corporation)

### 2.3. Role Assignment
```sql
SELECT r.id, r.name FROM roles r
JOIN user_roles ur ON ur.role_id = r.id
WHERE ur.user_id = 1;
```
* Roles: `admin` (ID: 1) and `platform_super_admin` (ID: 4).

### 2.4. Duplicate & Identity Collision Check
```sql
SELECT email, count(*) FROM users GROUP BY email HAVING count(*) > 1;
-- 0 duplicate rows returned
SELECT u.id, u.email FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles r ON r.id = ur.role_id
WHERE r.name = 'platform_super_admin';
-- Exactly 1 row returned: User ID 1 (admin@servicepulse.uz)
```

### 2.5. Identification of Target Database Modified by CLI
* The bootstrap CLI script (`python -m backend.app.cli.bootstrap_owner`) targeted the active connection configured in `backend/app/core/config.py` (`POSTGRES_DB=servicepulse`), which is the persistent development database.
* The test database (`servicepulse_test`) has all Alembic migrations applied through `20261115_1200_e7f8a9b0c1d2_platform_owner_access_governance.py`, but contains 0 persistent records in `platform_settings` and `users` (as verified by `SELECT count(*) FROM platform_settings;` returning `0`). Test runners populate and roll back `servicepulse_test` dynamically.

---

## 3. Real Owner Login Verification

A live, programmatic authentication audit was executed against the running backend container using `scripts/audit_verify_login.py`. In accordance with security guidelines, no credentials, password hashes, or token secrets were printed or logged.

### Verification Execution Results
```
[1] Login API Endpoint Status:               PASS (HTTP 200 OK)
[2] JWT Structure & Claims:                   PASS (Valid Bearer, expires_in=900s, sub="1", roles=["platform_super_admin", "admin"])
[3] Current Profile Endpoint (/auth/me):      PASS (User ID 1, admin@servicepulse.uz, is_active=true, is_superuser=true)
[4] Primary Owner Identification Claim:       PASS (is_primary_owner: true)
[5] Platform Dashboard Access:                PASS (HTTP 200 OK, full platform intelligence payload accessible)
[6] Session Invalidation on Logout:           FAIL (HTTP 200 on /refresh using revoked refresh token)
```

---

## 4. Critical Security Defect: Refresh Token Revocation Bypass

### 4.1. Defect Classification
* **Severity:** CRITICAL
* **Component:** `backend/app/services/auth_service.py`
* **Affected Functions:** `AuthService.refresh_access_token` (lines 168–184) and `AuthService.create_user_tokens` (lines 105–121)
* **Impact:** Broken Session Revocation. When a user explicitly logs out via `POST /api/v1/auth/logout`, active refresh tokens marked `revoked = True` in the database are not rejected by `POST /api/v1/auth/refresh`. An attacker in possession of a refresh token can continue minting valid access tokens indefinitely until the cryptographic expiry of the JWT signature (7 days).

### 4.2. Root Cause Analysis

#### Bug 1: Unsynchronized `jti` in Token Generation (`create_user_tokens`)
In `backend/app/services/auth_service.py`:
```python
jti = str(uuid.uuid4())
access_token = create_access_token(
    subject=str(user.id),
    claims=claims,
    expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
)
# DEFECT: create_refresh_token() is called without passing jti!
refresh_token = create_refresh_token(
    subject=str(user.id),
    expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
)
# In database, a completely unrelated jti is stored:
db_token = RefreshToken(
    user_id=user.id,
    token_hash=hash_token(refresh_token),
    jti=jti, # Stored jti does NOT match the jti embedded in refresh_token JWT!
    expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    revoked=False,
)
```
Because `create_refresh_token(subject=str(user.id))` internally calls `uuid.uuid4()` if `jti` is omitted, the `jti` claim in the signed JWT payload differs from the `jti` column in the database `refresh_tokens` table.

#### Bug 2: Missing Revocation Verification in `refresh_access_token`
In `backend/app/services/auth_service.py`:
```python
@staticmethod
async def refresh_access_token(refresh_token_str: str, db: AsyncSession) -> Token:
    try:
        payload = decode_token(refresh_token_str)
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Fetch active user
    ...
    # Query database for unrevoked tokens:
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        ).order_by(RefreshToken.created_at.desc())
    )
    latest_token = res.scalars().first()
    if latest_token:
        latest_token.revoked = True

    # CRITICAL DEFECT: If latest_token is None (e.g. after logout_user set all tokens to revoked=True),
    # the function NEVER raises an HTTPException! It simply skips revocation and creates new tokens:
    new_tokens = await AuthService.create_user_tokens(user, db)
    await db.commit()
    return new_tokens # SUCCESS 200 OK despite all DB records being revoked!
```

### 4.3. Remediation Specification
To remediate this vulnerability:
1. In `create_user_tokens`: Pass `jti=jti` to `create_refresh_token`:
   ```python
   refresh_token = create_refresh_token(
       subject=str(user.id),
       expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
       jti=jti,
   )
   ```
2. In `refresh_access_token`: Verify incoming token by its cryptographic hash or synchronized `jti`, and raise HTTP 401 if unrevoked record is not found:
   ```python
   incoming_hash = hash_token(refresh_token_str)
   res = await db.execute(
       select(RefreshToken).where(
           RefreshToken.user_id == user.id,
           RefreshToken.token_hash == incoming_hash,
           RefreshToken.revoked == False,
           RefreshToken.expires_at > datetime.now(timezone.utc)
       )
   )
   active_token = res.scalar_one_or_none()
   if not active_token:
       raise HTTPException(
           status_code=status.HTTP_401_UNAUTHORIZED,
           detail="Refresh token is invalid, expired, or has been revoked."
       )
   active_token.revoked = True
   ```

*Per the audit instructions, no application files were modified during this audit. The defect is documented here as an actionable blocker requiring remediation prior to final release.*

---

## 5. Database-Authoritative Owner Authorization Audit

The authorization gate for Primary Platform Owner was audited in `backend/app/core/dependencies.py`:

```python
async def is_primary_platform_owner(user: User, db: AsyncSession) -> bool:
    """
    Determine if the user is the designated Primary Platform Owner.
    Authoritatively checks the PlatformSettings singleton record in PostgreSQL.
    Does NOT rely on JWT claim or frontend state.
    """
    if not user.is_active:
        return False
    res = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    settings = res.scalar_one_or_none()
    if settings and settings.primary_owner_id is not None:
        return user.id == settings.primary_owner_id
    return user.is_superuser
```

### Empirical Authorization Assertions (`backend/tests/audit_test_owner_authorization.py`)
Executed synchronously in the container (`pytest backend/tests/audit_test_owner_authorization.py -v`):
1. **Primary Owner Approval Authority:** Returns `HTTP 200 OK` (**PASS**).
2. **Second Super Administrator:** User with `is_superuser=True` and `platform_super_admin` role who is not the DB `primary_owner_id` receives `HTTP 403 Forbidden` (`"Primary platform owner authority is required"`) (**PASS**).
3. **Company Administrator:** Receives `HTTP 403 Forbidden` (**PASS**).
4. **Employee:** Receives `HTTP 403 Forbidden` (**PASS**).
5. **Stale JWT Claim Invalidation:** A handcrafted JWT with claim `"is_primary_owner": true` for a former owner was tested after transferring `primary_owner_id` in the database. The endpoint dynamically queried PostgreSQL and returned `HTTP 403 Forbidden` (**PASS**).
6. **Live Transfer Resilience:** The newly designated owner in PostgreSQL succeeded immediately on the same endpoint without token reissuance (**PASS**).

---

## 6. Access Approval Security Audit

An automated security audit test suite (`backend/tests/audit_test_access_security.py`) was constructed and executed against the test environment. All 6 security test scenarios passed (6/6).

### 6.1. Coverage of All 7 Request Types
Every access request category defined in the platform governance schema was verified through submission and Primary Owner approval:
1. `organization_registration` (**PASS**)
2. `organization_membership` (**PASS**)
3. `employee_access` (**PASS**)
4. `support_access` (**PASS**)
5. `it_admin_access` (**PASS**)
6. `company_admin_access` (**PASS**)
7. `executive_access` (**PASS**)

### 6.2. Privilege Escalation & Self-Approval Prevention
* **Applicant Role Self-Assignment:** Applicants cannot grant themselves privileged roles. Any request submitted by a user or company admin remains in status `'pending'` until explicitly reviewed by the Primary Owner.
* **Self-Approval:** Company Admin attempting to approve their own request for `executive_access` received `HTTP 403 Forbidden` (**PASS**).
* **Employee Approval Block:** Standard employees attempting approval received `HTTP 403 Forbidden` (**PASS**).

### 6.3. Company Admin Tenant Boundaries
* **Cross-Tenant Request Submission:** Company Admin for Tenant 1 attempting to submit an access request specifying `organization_id=2` received `HTTP 403 Forbidden` (`"Company Admins can only submit access requests for their own organization."`) (**PASS**).
* **Cross-Tenant Request Inspection:** Company Admin for Tenant 1 attempting to GET `/api/v1/access-requests/{tenant2_request_id}` received `HTTP 403 Forbidden` (`"Access denied."`) (**PASS**).

### 6.4. Single-Use Invitation Enforcement
* Single-use invitation (`max_uses=1`) created by Company Admin.
* First redemption via `/api/v1/auth/join-organization`: `HTTP 201 Created` with valid token pair (**PASS**).
* Second redemption using the exact same code: `HTTP 400 Bad Request` with `"This invitation has reached its maximum allowed uses."` (**PASS**). Single-use token rotation is strictly enforced.

### 6.5. Concurrency & Race Condition Resilience
* Two concurrent approval requests (`asyncio.gather`) were dispatched simultaneously against the same pending access request.
* Exactly one request succeeded with `HTTP 200 OK` (`status: approved`), and the second request was safely rejected with `HTTP 400 Bad Request` (`"Cannot approve request with status 'approved'"`) (**PASS**).
* Verified that duplicate accounts or duplicate tenant provisioning cannot be triggered by race conditions.

### 6.6. Rejection Validation & Audit Log Persistence
* Rejection with empty reason: `HTTP 422 Unprocessable Entity` (**PASS**).
* Rejection with whitespace or < 3 characters: `HTTP 422 Unprocessable Entity` (**PASS**).
* Rejection with valid reason (`"Applicant background verification inconclusive."`):
  * Updated request status to `'rejected'`.
  * Persisted `rejection_reason` in database.
  * Stored `reviewed_by_id` as the Primary Owner.
  * Created immutable `AuditLog` row with `action="access_request_rejected"`, `target_resource="access_request"`, and reason details (**PASS**).

---

## 7. Database Isolation & Side-Effects Audit

A read-only inspection was performed on the persistent development database (`servicepulse`) and compared against the baseline documented in `docs/reports/servicepulse-database-side-effects-audit.md`:

### Table Inventory Comparison

| Table | Baseline Count | Current Dev DB Count (`servicepulse`) | Change Explanation |
| :--- | :--- | :--- | :--- |
| `users` | 24 | **24** | Intact. Baseline users #1–24 preserved. Zero unwanted accounts. |
| `organizations` | 6 | **6** | Intact. Organizations #1–6 preserved. |
| `organization_requests` | 3 | **3** | Intact. Request #3 preserved. |
| `organization_invitations` | 4 | **4** | Intact. Invite #4 preserved. |
| `incidents` | 16 | **16** | Intact. Incident #16 resolved, intact. |
| `incident_events` | 60 | **60** | Intact. Events #56–60 preserved. |
| `notifications` | 16 | **16** | Intact. Notifications #15, #16 preserved. |
| `tickets` | 1 | **1** | Intact. Screenshot fixture ticket #1 preserved. |
| `ticket_comments` | 1 | **1** | Intact. Screenshot fixture comment #1 preserved. |
| `software_requests` | 21 | **21** | Intact. Request #21 preserved. |
| `device_state_transitions` | 35 | **35** | Intact. Transitions #33–35 preserved. |
| `platform_settings` | 0 | **1** | Added: Singleton configuration row designating User #1 as Primary Owner. |
| `access_requests` | 0 | **4** | Added: 4 realistic demonstration governance requests seeded by `init_db.py`. |
| `audit_logs` | 375 | **385** | Added: 10 operational audit records (bootstrap, seed initialization, and login check). |

### Test Database Isolation Proof
The test database (`servicepulse_test`) was inspected directly via PostgreSQL command:
* `SELECT count(*) FROM users;` -> `0`
* `SELECT count(*) FROM platform_settings;` -> `0`
* `SELECT count(*) FROM access_requests;` -> `0`
All pytest suites executed in transactionally isolated test runners with automatic rollbacks, ensuring zero pollution of development or test data.

---

## 8. Branding & Academic Metadata Verification

A comprehensive repository scan was performed targeting legacy university references (`TATU`, `tatu.uz`, `university`, `thesis`, `BMI`):

1. **Frontend Active UI (`frontend/src/`):**
   * `git grep -i -E "tatu\.uz|\btatu\b|university|thesis" frontend/src/` returned **0 matches** (exit code 1).
2. **Frontend Locales (`frontend/src/i18n/locales/`):**
   * English (`en.json`), Russian (`ru.json`), and Uzbek (`uz.json`) contain **0 university or thesis branding strings**.
3. **Backend Application (`backend/app/`):**
   * Zero active runtime references. The only match is in `backend/app/db/init_db.py`, which is an explicit sanitization rule that cleanses any legacy `"TATU"` strings from demo organizations.
4. **Historical Screenshot Preservation:**
   * `git status --porcelain docs/screenshots/*before*` returned **0 modifications**. All original baseline screenshots remain untouched.

---

## 9. Test Execution Evidence & Code Quality

### 9.1. Backend Regression Suite
* Command: `docker compose exec backend pytest backend/tests/test_platform_owner_bootstrap.py backend/tests/test_auth_registration.py backend/tests/test_multi_tenant_api.py -v`
* Output: **`32 passed in 111.81s (0:01:51)`**
* Breakdown:
  * `test_platform_owner_bootstrap.py`: 9/9 passed
  * `test_auth_registration.py`: 19/19 passed
  * `test_multi_tenant_api.py`: 4/4 passed

### 9.2. Frontend Vitest Suite
* Command: `cd frontend; npm test`
* Output: **`Test Files 14 passed (14) | Tests 57 passed (57) in 49.54s`**
* Key suites verified:
  * `owner_governance.test.tsx` (6/6 passed)
  * `auth_registration.test.tsx` (5/5 passed)
  * `dashboards.test.tsx` (5/5 passed)
  * `login.test.tsx` (4/4 passed)

### 9.3. Frontend Production Build
* Command: `cd frontend; npm run build` (`tsc && vite build`)
* Output: **`built in 22.17s`** (Exit code 0). Clean production bundle generated in `dist/`.

### 9.4. Linters & Git Integrity
* **ESLint:** `eslint src --max-warnings 0` -> **0 warnings, Exit code 0**.
* **Ruff:** `ruff check .` -> **All checks passed! Exit code 0**.
* **Git diff check:** `git diff --check` -> **Clean, Exit code 0**.
* **Branch Status:** On branch `feature/platform-owner-access-control`, based on `ece18ab98e551b21b15367fa96c83a48cbee92ff`. Zero secrets or credentials committed.

---

## 10. Final Decision & Action Items

### Final Status: **CONDITIONAL PASS**

The milestone demonstrates exceptional architectural quality, robust database-backed authorization, and complete UI/API parity for Centralized Access Governance. 

### Mandatory Pre-Release Remediation
Prior to merging or advancing to production deployment, the following security patch must be applied and verified:

```python
# File: backend/app/services/auth_service.py
# In refresh_access_token():
active_token = (await db.execute(
    select(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.token_hash == hash_token(refresh_token_str),
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    )
)).scalar_one_or_none()

if not active_token:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token has been revoked, expired, or is invalid."
    )

active_token.revoked = True
```

Once this patch is applied and verified with a session invalidation test (`scripts/audit_verify_login.py` returning PASS on logout invalidation), the milestone will achieve **FULL UNCONDITIONAL PASS**.
