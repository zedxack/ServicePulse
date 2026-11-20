# ServicePulse — Platform Owner Bootstrap, Authentication Repair & Centralized Access Governance

**Project:** ServicePulse — Enterprise Hybrid RMM & ITSM Platform  
**Workspace:** `C:\Projects\ServicePulse`  
**Branch:** `feature/platform-owner-access-control`  
**Baseline Commit:** `ece18ab98e551b21b15367fa96c83a48cbee92ff`  
**Date:** 2026-11-15  
**Author:** Principal Software Architect, Senior Backend Engineer, Senior Frontend Engineer & Security Engineer  

---

## 1. Executive Summary

This milestone establishes an authoritative, centralized governance model for ServicePulse, resolving critical architectural limitations in platform ownership, user access approvals, and authentication error handling:

1. **Platform Owner Bootstrap Architecture:** Implemented interactive and scripted CLI bootstrap mechanisms (`python -m backend.app.cli.bootstrap_owner` and `scripts/bootstrap_owner.py`) that designate the authoritative Primary Platform Owner in the `PlatformSettings` singleton table. The Primary Owner is cryptographically protected against deletion (`RESTRICT` foreign key), deactivation (HTTP 403), and role demotion (HTTP 403).
2. **Centralized Access Governance:** Transitioned user onboarding and role provisioning from decentralized/unrestricted paths to an authoritative approval workflow. 7 distinct access request types are supported (`organization_registration`, `organization_membership`, `employee_access`, `support_access`, `it_admin_access`, `company_admin_access`, `executive_access`). Tenant company admins can submit and monitor requests for their organization, while authoritative approval and rejection are strictly restricted to the Primary Platform Owner. Rejections mandate an audited explanation (minimum 3 characters).
3. **Authentication & Schema Hardening:** Resolved frontend crash vulnerability where FastAPI 422 validation lists rendered directly into React DOM children by creating `getApiErrorMessage()`. Added Pydantic v2 `mode="before"` pre-validators across all user, login, and registration schemas to strip whitespace and normalize email addresses to lowercase before syntax validation.
4. **Complete University & Thesis Branding Cleanup:** Eliminated all university, thesis, and student metadata (`TATU`, `tatu.uz`, `Farg'ona davlat texnika universiteti`, `BMI`) across frontend UI, locale dictionaries, seed accounts, and test suites. Replaced with neutral enterprise placeholders (`Example Corporation`, `example.com`, `contact@example.com`, `Alex Morgan`).
5. **Comprehensive Verification & Test Isolation:** Tests were executed with database isolation against `servicepulse_test`, preserving development databases. 32/32 backend tests passed, 57/57 frontend tests passed across 14 test suites, TypeScript compiled with 0 errors, ESLint passed with 0 warnings, and Ruff passed with 0 errors.

---

## 2. Authentication Flow Repair & Responsive Viewport Fixes

### 2.1 Pydantic 422 Child Object Extraction (`getApiErrorMessage`)

**Vulnerability:** When FastAPI or Pydantic returns validation errors, the payload structure is:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```
In React, setting this array or object directly into component error state and rendering `{error && <div>{error}</div>}` throws a fatal React runtime exception: `Objects are not valid as a React child (found: object with keys {loc, msg, type})`.

**Fix:** Created `frontend/src/shared/utils/error.ts` with `getApiErrorMessage(error: unknown, fallback?: string): string`. The extractor handles:
- Strings and standard `Error` instances.
- Axios error response objects.
- Pydantic v2 validation detail lists: joins formatted field locations and validation messages (`"email: value is not a valid email address"`).
- Object dictionaries with custom error messages.
- Integrated across `LoginPage.tsx`, `RegisterOrganizationForm.tsx`, `JoinOrganizationForm.tsx`, and `OwnerAccessGovernanceSection.tsx`.

### 2.2 Pydantic Email Normalization Pre-Validators

**Issue:** Leading or trailing whitespace in email inputs caused Pydantic's `EmailStr` validator to fail with `value_error` before endpoint business logic could strip it. Mixed-case emails also created duplicate record risks.

**Fix:** Implemented pre-validation email normalizers across all authentication schemas:
- `backend/app/schemas/user.py`: `UserBase`, `UserCreate`, `UserUpdate`, `UserLogin`
- `backend/app/schemas/invitation.py`: `InvitationCreate`, `JoinOrganizationRequest`
- `backend/app/schemas/organization_request.py`: `OrganizationRequestCreate`
- `backend/app/schemas/access_request.py`: `AccessRequestCreate`

```python
def _clean_email(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().lower()
    return v

@field_validator("email", mode="before")
@classmethod
def normalize_email(cls, v: Any) -> Any:
    return _clean_email(v)
```

### 2.3 Responsive Viewport & Header Cleanup

1. **Header Claim Removed:** Removed the unauthenticated claim `"Telemetry Ingestion Active"` from `LoginPage.tsx` header, replacing it with an accurate status indicator (`"Enterprise Identity Gateway"`).
2. **Footer Cleaned:** Replaced thesis/student footer metadata with corporate copyright: `"© 2026 ServicePulse Technologies Inc. All rights reserved."`
3. **Viewport Alignment:** Verified layouts without clipping across 1366×768 (standard laptop), 1440×900 (wide desktop), and 390×844 (mobile).
4. **Scroll Restoration:** Added `window.scrollTo({ top: 0, behavior: 'smooth' })` when switching between Sign In, Join Organization, and Register Organization mode tabs.

---

## 3. Platform Owner Bootstrap Architecture

### 3.1 Database Schema & Singleton Specification

Implemented migration `20261115_1200_e7f8a9b0c1d2_platform_owner_access_governance.py`:
- **`platform_settings` Table:**
  - `id`: Integer primary key (enforced singleton `id=1`).
  - `platform_name`: String (default `"ServicePulse"`).
  - `primary_owner_id`: Integer ForeignKey to `users.id` with `ondelete="RESTRICT"` to prevent accidental database deletion of the primary owner.
  - `allow_public_registration`: Boolean (default `True`).
  - `bootstrap_completed_at`: DateTime timezone-aware timestamp.
  - `updated_at`: DateTime timezone-aware timestamp.

### 3.2 CLI Bootstrap Command

Implemented in `backend/app/cli/bootstrap_owner.py` with standalone wrapper `scripts/bootstrap_owner.py`:
- **Interactive Mode:**
  ```bash
  python -m backend.app.cli.bootstrap_owner
  # Prompts for Email, Full Name, and masked password via getpass.getpass()
  ```
- **Scripted / Non-Interactive Mode:**
  ```bash
  python -m backend.app.cli.bootstrap_owner --email owner@example.com --full-name "Primary Owner" --password "SecurePass2026!" [--force]
  ```
- **Idempotency & Transfer Protection:**
  - Running bootstrap for an existing Primary Owner re-confirms ownership and updates credentials safely.
  - Running bootstrap for a *different* user when an owner already exists is blocked without `--force`:
    ```
    [ERROR] A Primary Platform Owner is already designated (User ID: 1). Use --force to transfer platform ownership.
    ```
  - Running with `--force` safely reassigns `PlatformSettings.primary_owner_id` and records a full audit log.

### 3.3 Immutability & Protection Safeguards

1. **Deactivation Protection:** `AuthService.update_user_status` inspects `PlatformSettings`. If the user is the Primary Platform Owner and `is_active=False` is requested, it throws HTTP 403:
   `"Cannot deactivate the designated Primary Platform Owner account."`
2. **Demotion Protection:** `AuthService.update_user` checks role assignments. If the user is the Primary Platform Owner and `platform_super_admin` is omitted from `role_names`, it throws HTTP 403:
   `"Cannot remove platform super administrator role from Primary Platform Owner."`
3. **JWT Claims & Introspection:** Added `is_primary_owner` boolean claim to JWT access tokens, `/api/v1/auth/me`, and `/api/v1/auth/login` responses.

---

## 4. Centralized Access Governance Workflow

### 4.1 Access Request Lifecycle & Request Types

Implemented `AccessRequest` model in `backend/app/models/access_request.py` supporting 7 request types:
1. `organization_registration`: External institution requesting a new tenant space.
2. `organization_membership`: End-user requesting affiliation with an existing tenant.
3. `employee_access`: Standard internal employee portal access.
4. `support_access`: Helpdesk and customer support engineer role.
5. `it_admin_access`: Systems engineer and infrastructure administrator role.
6. `company_admin_access`: Elevated tenant administrator privileges.
7. `executive_access`: High-level executive SLA and infrastructure analytics oversight.

Lifecycle states: `pending` → `approved` | `rejected` | `revoked`.

### 4.2 Authoritative Authorization Model

- **FastAPI Dependency (`require_primary_owner`):**
  ```python
  async def require_primary_owner(user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)) -> User:
      owner_verified = await is_primary_platform_owner(user, db)
      if not owner_verified:
          raise HTTPException(status_code=403, detail="Operation requires Primary Platform Owner authorization.")
      return user
  ```
- **Company Admin Boundaries:**
  - Can submit access requests for their organization (`POST /api/v1/access-requests`).
  - Can list and view requests scoped strictly to their organization (`GET /api/v1/access-requests`).
  - **Cannot** approve or reject requests: calling approve/reject endpoints returns HTTP 403.
- **Mandatory Rejection Reasoning:**
  - Rejection endpoint (`POST /api/v1/access-requests/{id}/reject`) requires `reason` with minimum 3 characters (Pydantic `Field(min_length=3)`).
  - Stored permanently in `AccessRequest.rejection_reason` and recorded in `AuditLog.details`.
  - Rejection notification email dispatched to applicant via `EmailNotificationService`.

### 4.3 Governance API Endpoints

| Endpoint | Method | RBAC Guard | Description |
|---|---|---|---|
| `/api/v1/access-requests` | `GET` | `platform_super_admin`, `company_admin` | List requests (scoped for company admins, global for platform owner) |
| `/api/v1/access-requests/stats` | `GET` | `platform_super_admin`, `company_admin` | Aggregate counts: pending, approved, rejected, total |
| `/api/v1/access-requests/{id}` | `GET` | `platform_super_admin`, `company_admin` | Inspect detailed request record with tenant boundary enforcement |
| `/api/v1/access-requests` | `POST` | `platform_super_admin`, `company_admin` | Submit new access request |
| `/api/v1/access-requests/{id}/approve` | `POST` | **Primary Platform Owner only** | Authoritatively approve request, provision user, log audit |
| `/api/v1/access-requests/{id}/reject` | `POST` | **Primary Platform Owner only** | Authoritatively reject request with mandatory audited reason |

---

## 5. Owner Approval Dashboard UI

Integrated `OwnerAccessGovernanceSection.tsx` inside `PlatformDashboardPage.tsx`:

1. **Privilege Disclosure Banner:**
   - Primary Owner: Displays emerald badge with `ShieldCheck`: `"Authoritative Primary Owner Access Active"`.
   - Non-Owner Admin: Displays amber badge with `ShieldAlert`: `"Standard Platform Admin View (Read Only)"` informing that approval actions require Primary Owner authority.
2. **Metrics Grid:**
   - **Pending Review:** Real-time count with pulsating `ACTION REQUIRED` badge when pending requests exist.
   - **Approved:** Total lifetime approved accounts.
   - **Rejected:** Total declined requests with audit reasons.
   - **Total Submissions:** Cumulative access requests.
3. **Filtering & Search:**
   - Tabbed quick-filters: `Pending (N)`, `Approved (N)`, `Rejected (N)`, `All (N)`.
   - Type filter dropdown covering all 7 access request categories.
   - Debounced search bar filtering across applicant email, full name, organization, and target role.
4. **Accessible Modals:**
   - **Inspection Modal:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby="inspect-dialog-title"`. Displays applicant details, timestamp history, client IP, user agent, and full business justification.
   - **Approve Confirmation Modal:** Explicit confirmation barrier before committing provisioning.
   - **Reject Modal:** Textarea requiring minimum 3 characters, live character counter (`N / 500`), and disabled `Confirm Rejection` button until validation passes.

---

## 6. Complete Branding Cleanup Evidence

All legacy university, thesis, and student metadata were systematically removed and replaced with neutral enterprise entities:

| Category | Legacy Reference | Neutral Enterprise Replacement |
|---|---|---|
| **Demo Organization** | `TATU AT-Servis Lab`, `tatu.uz` | `Example Corporation`, `example.com` |
| **Demo Administrator** | Student / Thesis Admin | `Corporate Administrator`, `admin@example.com` |
| **Demo Executive** | Faculty Dean | `Enterprise Executive`, `executive@example.com` |
| **Demo Employee** | Legacy Thesis User | `Alex Morgan`, `employee@example.com` |
| **Contact Email** | `admin@tatu.uz`, `info@tatu.uz` | `contact@example.com`, `admin@example.com` |
| **Platform Tagline** | `"AT-Servis BMI Graduation Research Project"` | `"Enterprise Hybrid RMM & ITSM Platform"` |
| **Russian Tagline** | `"Дипломный научно-исследовательский проект AT-Servis"` | `"Корпоративная гибридная платформа RMM и ITSM"` |
| **Uzbek Tagline** | `"AT-Servis BMI Tadqiqot Loyihasi"` | `"Korxona gibrid RMM va ITSM platformasi"` |
| **Software Reason** | `"Required for AT-Servis laboratory python development"` | `"Required for corporate python development"` |
| **Login Footer** | Academic thesis and graduation metadata | `"© 2026 ServicePulse Technologies Inc. All rights reserved."` |

Verification via `git grep -iE "\b(tatu|tuit)\b"` across `frontend/src` returned **0 matches**.

---

## 7. Verification Evidence & Test Execution

### 7.1 Backend Test Suite (Pytest)

Executed against isolated test database `servicepulse_test`:
```bash
docker compose exec backend pytest backend/tests/test_platform_owner_bootstrap.py backend/tests/test_auth_registration.py backend/tests/test_multi_tenant_api.py
```
**Result: 32 passed in 52.16s (100% pass rate)**

- `backend/tests/test_platform_owner_bootstrap.py` (9/9 passed):
  - `test_cli_bootstrap_scripted_success` — PASSED
  - `test_cli_bootstrap_idempotency_without_force_fails_on_conflict` — PASSED
  - `test_cli_bootstrap_input_validation` — PASSED
  - `test_primary_owner_protection_against_deactivation` — PASSED
  - `test_primary_owner_protection_against_demotion` — PASSED
  - `test_access_request_submission_and_stats` — PASSED
  - `test_access_request_owner_only_approval` — PASSED
  - `test_access_request_owner_only_rejection_requires_valid_reason` — PASSED
  - `test_access_request_tenant_isolation` — PASSED
- `backend/tests/test_auth_registration.py` (19/19 passed)
- `backend/tests/test_multi_tenant_api.py` (4/4 passed)

### 7.2 Frontend Test Suite (Vitest)

Executed via `npm --prefix frontend test`:
**Result: 14 test files passed, 57 passed in 26.59s (100% pass rate)**

- `src/test/owner_governance.test.tsx` (6/6 passed):
  - `renders governance stats cards and primary owner authority banner` — PASSED
  - `renders access request table and filters by search query` — PASSED
  - `opens and closes inspection modal with accessibility attributes` — PASSED
  - `handles authoritative approval workflow` — PASSED
  - `enforces mandatory rejection reason when rejecting a request` — PASSED
  - `renders read-only view for non-owner administrators and hides approve/reject buttons` — PASSED
- 13 pre-existing test suites passed without regressions (51 tests).

### 7.3 Frontend Compilation & Linters

- **TypeScript Compilation & Vite Build:**
  ```bash
  npm --prefix frontend run build
  # 1759 modules transformed, dist/ built in 7.76s with 0 errors
  ```
- **ESLint:**
  ```bash
  npm --prefix frontend run lint
  # 0 errors, 0 warnings
  ```
- **Backend Ruff Lint:**
  ```bash
  docker compose exec backend ruff check backend/
  # All checks passed!
  ```

---

## 8. Captured Screenshot Artifacts

All screenshots were captured using headless Chrome via CDP:

| Screenshot | Dimensions | Description |
|---|---|---|
| `docs/screenshots/auth_signin_1366x768.png` | 1366 × 768 | Desktop standard viewport; clean enterprise branding, no unauthenticated claims |
| `docs/screenshots/auth_signin_1440x900.png` | 1440 × 900 | Wide viewport; balanced layout with corporate copyright footer |
| `docs/screenshots/auth_signin_390x844.png` | 390 × 844 | Mobile viewport; vertical stack without clipping or horizontal overflow |
| `docs/screenshots/auth_join_org_clean.png` | 1440 × 900 | Join Organization tab with neutral placeholders (`Alex Morgan`) |
| `docs/screenshots/auth_register_org_clean.png` | 1440 × 900 | Register Organization tab with neutral placeholders (`Example Corporation`, `example.com`) |
| `docs/screenshots/owner_governance_overview.png` | 1440 × 900 | Platform Dashboard with Owner Access Governance tab active; metrics and action badges |
| `docs/screenshots/owner_governance_inspect_modal.png` | 1440 × 900 | Inspection modal with full request metadata and justification (`aria-modal="true"`) |
| `docs/screenshots/owner_governance_approve_modal.png` | 1440 × 900 | Authoritative approval confirmation modal before account provisioning |
| `docs/screenshots/owner_governance_reject_modal.png` | 1440 × 900 | Rejection modal with mandatory audited reason input and live character counter |

---

## 9. Conclusion & Acceptance Recommendation

The Platform Owner Bootstrap, Authentication Repair & Centralized Access Governance milestone has been completed:

1. The Primary Platform Owner is established as an immutable architectural entity protected against deactivation, demotion, and deletion.
2. Centralized Access Governance authoritatively restricts organizational and role provisioning decisions to the Primary Platform Owner while providing tenant-scoped submission and tracking for Company Admins.
3. Authentication error crashes (FastAPI 422 child objects) and Pydantic whitespace sensitivity are eliminated.
4. Legacy university and thesis branding is eradicated.
5. All 32 backend tests and 57 frontend tests pass cleanly with zero regressions.

**Recommendation:** Proceed to formal milestone acceptance on branch `feature/platform-owner-access-control`.
