# ServicePulse — Secure Authentication, Registration & Organization Onboarding Engineering Report

**Author:** Muhammadyusuf Usmonov  
**Target Environment:** Enterprise IT Operations  
**System Identity:** ServicePulse Enterprise Hybrid RMM & ITSM Platform  
**Target Branch:** `feature/auth-registration-onboarding`  
**Base Commit:** `5973d638c5c95949f6c4a380315521c407f9f995`  
**Completion Date:** November 14, 2026  
**Status:** FULLY VERIFIED, AUDITED & ACCEPTED  

---

## 1. Executive Summary

This engineering delivery implements a comprehensive, production-grade authentication, user registration, and organization onboarding system for ServicePulse.

Key accomplishments:
1. **Unified Authentication Interface:** A responsive and modern React interface offering seamless switching between "Sign In", "Join with Invite", and "New Organization" registration flows.
2. **Invitation-Driven Tenant Registration:** Concurrency-safe atomic invitation redemption with role escalation guardrails, configurable usage caps, time limits, and cryptographic SHA-256 token hashing at rest.
3. **Pending-Approval Organization Onboarding:** An enterprise onboarding workflow where new tenant requests remain in a `pending` state until reviewed and approved by Platform Super Administrators, automatically provisioning the new tenant organization and initial Company Administrator.
4. **Pure In-Memory JWT Security Architecture:** Maintained zero persistence of JWT tokens in browser storage (`localStorage` / `sessionStorage`), completely mitigating XSS token harvesting vectors.
5. **Rate Limiting & Defensive Controls:** Sliding window rate limiters on public authentication, registration, and invitation endpoints preventing credential stuffing, registration spam, and invitation brute-forcing.
6. **Multi-Language Support (i18n):** Complete localized translations in Uzbek (`uz`), Russian (`ru`), and English (`en`).
7. **Email Notification Provider Abstraction:** Configurable SMTP and fallback Null providers ensuring clean notification dispatch without faking external delivery or logging sensitive credentials.
8. **E2E Docker Proxy Verification:** End-to-end integration verified through the Nginx reverse proxy across 11 scenarios and 30 assertions, including live worker-to-WebSocket delivery and full onboarding lifecycles.

---

## 2. Engineering Changes Summary

### 2.1 Backend Architecture

- **ORM Models (`backend/app/models/`):**
  - `OrganizationInvitation`: Table `organization_invitations` with `token_hash`, `token_prefix`, `max_uses`, `uses_count`, `expires_at`, `is_revoked`, and tenant/role foreign keys. Equipped with `lazy="selectin"` for asynchronous relationship loading.
  - `OrganizationRequest`: Table `organization_requests` with corporate metadata, contact details, Argon2id `hashed_password`, workflow `status` (`pending`, `approved`, `rejected`), reviewer audit keys, and `lazy="selectin"` foreign relationships.
  - Exported both models in `backend/app/models/__init__.py`.
- **Application Configuration (`backend/app/core/config.py`):**
  - Added SMTP parameters (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME`, `EMAIL_VERIFICATION_REQUIRED`).
  - Added rate limiting settings (`RATE_LIMIT_AUTH_PER_MINUTE`, `RATE_LIMIT_REGISTRATION_PER_MINUTE`).
- **Core Security & Rate Limiting (`backend/app/core/`):**
  - `rate_limiter.py`: Sliding window in-memory rate limiter with thread-safe locking, IP detection, and HTTP 429 Retry-After headers. Hardened reverse proxy client IP extraction to prioritize `X-Real-IP` and parse the rightmost hop of `X-Forwarded-For`.
  - `security.py`: Enhanced `validate_password_strength()` verifying 8+ characters, uppercase, lowercase, numbers, and special symbols.
- **Service Layer (`backend/app/services/`):**
  - `email_service.py`: Provider abstraction (`EmailProvider`, `SMTPEmailProvider`, `NullEmailProvider`) and transactional notification templates.
  - `invitation_service.py`: Concurrency-safe token pair generator, `with_for_update()` atomic redemption, role escalation guardrails, invitation validation, listing, and revocation.
  - `organization_request_service.py`: Onboarding request submission, super admin review, approval (with automatic Organization and Company Admin User provisioning), and rejection.
- **API Endpoints (`backend/app/api/v1/`):**
  - `endpoints/auth.py`: Added `/join-organization`, `/invitations/validate`, `/organization-requests`, and `/invitations` CRUD with explicit rate limiter dependencies.
  - `endpoints/platform.py`: Added `/platform/organization-requests` list, detail, approve, and reject endpoints restricted to Platform Super Admin.
  - `api.py`: Mounted `/platform` router.
- **Database Migrations (`backend/migrations/versions/`):**
  - Revision `d5e6f7a8b9c0`: `20261114_2000_d5e6f7a8b9c0_auth_registration_onboarding.py` creating both tables with indexes and foreign keys.

### 2.2 Frontend Architecture

- **Types & API Client (`frontend/src/shared/`):**
  - `types/auth.ts`: Added schemas for invitations, validation, joining, and organization requests.
  - `api/auth.ts`: Added HTTP client methods for all onboarding endpoints.
- **Auth Context (`frontend/src/features/auth/AuthContext.tsx`):**
  - Added `joinOrganization()` method that redeems tokens, sets in-memory JWT, fetches user profile, and establishes authenticated session.
- **Component Implementations (`frontend/src/features/auth/`):**
  - `PasswordStrengthMeter.tsx`: Interactive strength progress meter and criteria checklist.
  - `JoinOrganizationForm.tsx`: Invitation code verification, corporate details, password visibility toggle, password confirmation check, and immediate sign-in.
  - `RegisterOrganizationForm.tsx`: Organization onboarding form with pending approval confirmation screen.
  - `LoginPage.tsx`: Unified tabbed interface, password visibility toggle, removed dev shortcuts from normal view.
- **Localization (`frontend/src/i18n/locales/`):**
  - Added complete dictionary entries to `en.json`, `ru.json`, and `uz.json`.

---

## 3. Security & Architecture Audit

### 3.1 Rate Limiting Architecture & Proxy Security

- **Reverse Proxy Header Hardening:**
  When deployed behind reverse proxies (Nginx / Caddy), clients might attempt to spoof IP addresses by supplying fake `X-Forwarded-For` headers. The rate limiter extraction was hardened:
  1. `X-Real-IP` is prioritized, as Nginx and Caddy explicitly overwrite this header with `$remote_addr` or `{remote_host}`.
  2. If evaluating `X-Forwarded-For`, the algorithm takes the rightmost hop (`split(",")[-1]`) representing the peer connecting directly to the proxy, completely neutralizing attacker-prepended IP chains.
  3. Direct connection IP (`request.client.host`) serves as fallback.
- **Process-Local Memory & Horizontal Scaling:**
  - *Current Design:* Rate limiting utilizes an in-process sliding window (`collections.deque` timestamps per key) protected by `asyncio.Lock()`.
  - *Lifecycle:* Process restarts reset in-memory buckets; multi-worker Uvicorn configurations partition rate limit tracking across processes.
  - *Production Recommendation:* For high-availability multi-replica deployments, edge rate limiting via Nginx `limit_req_zone` or an external Redis sliding window with atomic Lua scripts is recommended. For single-container or small enterprise deployments, the process-local limiter provides robust protection against brute-force attacks with zero external operational dependencies.

### 3.2 Invitation & Organization Approval Security

- **Atomic Redemption:**
  Invitations are locked using `with_for_update()` in PostgreSQL during redemption to prevent race conditions when multiple concurrent clients attempt to redeem the final remaining use of a token.
- **Role Escalation Barriers:**
  - Company Admins can only generate invitations for roles within their organization hierarchy (e.g., `employee`, `technician`). Attempts to generate invitations for `platform_super_admin` or `company_admin` are rejected with HTTP 403.
  - Employee users are forbidden from generating invitations (`POST /auth/invitations` returns HTTP 403).
  - Employee users are forbidden from approving organization onboarding requests (`POST /platform/organization-requests/{id}/approve` returns HTTP 403).
- **Token Security at Rest:**
  Only a SHA-256 hash of the invitation token is stored in the database. The raw token is displayed only once upon generation and cannot be recovered from the database.
- **Credential Privacy:**
  Password hashes (Argon2id) and internal tokens are never serialized or returned in any API responses (`/auth/me`, `/auth/users`, `/platform/organization-requests`).

### 3.3 Email Provider Verification & Operational Safety

- **Provider Abstraction:**
  ServicePulse implements `SMTPEmailProvider` alongside a safe `NullEmailProvider`.
- **Safe Fallback Behavior:**
  When SMTP credentials are not configured (`SMTP_HOST` empty), the system falls back to `NullEmailProvider`, logging an explicit warning without raising unhandled exceptions or falsely claiming emails were delivered to external mailboxes.
- **Token & Secret Redaction:**
  Email notification logs never record plain passwords, reset tokens, or SMTP authentication credentials.
- **Required SMTP Environment Variables:**
  ```ini
  SMTP_HOST=smtp.example.com
  SMTP_PORT=587
  SMTP_USER=user@example.com
  SMTP_PASSWORD=secret-smtp-password
  SMTP_TLS=true
  EMAILS_FROM_EMAIL=no-reply@servicepulse.uz
  EMAILS_FROM_NAME=ServicePulse
  EMAIL_VERIFICATION_REQUIRED=false
  ```

---

## 4. Comprehensive Verification Results

### 4.1 Backend Test Suite (Docker PostgreSQL Environment)

- **Auth & Registration Test Suite:** `backend/tests/test_auth_registration.py`
  - Total Scenarios: 19 / 19 passed
  - Execution Time: 36.33s
  - Exit Code: 0
  - Coverage Summary:
    1. `test_login_successful_and_returns_tokens` — PASSED
    2. `test_login_invalid_credentials_rejected` — PASSED
    3. `test_generate_invitation_success_company_admin` — PASSED
    4. `test_generate_invitation_escalation_blocked` — PASSED
    5. `test_validate_invitation_valid_code` — PASSED
    6. `test_validate_invitation_invalid_or_expired` — PASSED
    7. `test_join_organization_success` — PASSED
    8. `test_join_organization_exhausted_uses_blocked` — PASSED
    9. `test_join_organization_revoked_invitation_blocked` — PASSED
    10. `test_join_organization_weak_password_rejected` — PASSED
    11. `test_submit_organization_request_pending` — PASSED
    12. `test_approve_organization_request_platform_super_admin` — PASSED
    13. `test_reject_organization_request` — PASSED
    14. `test_rate_limiting_enforced` — PASSED
    15. `test_reverse_proxy_header_spoofing_prevented` — PASSED
    16. `test_employee_cannot_issue_invitations` — PASSED
    17. `test_employee_cannot_approve_organization_request` — PASSED
    18. `test_duplicate_email_registration_blocked` — PASSED
    19. `test_password_hashes_never_returned_in_api` — PASSED

- **Full Backend Regression Suite:**
  - Command: `docker compose exec backend pytest backend/tests -q`
  - Total Passed: 93 / 93 passed (including PostgreSQL advisory lock and all STEP 1–5.4 tests)
  - Execution Time: 167.96s
  - Exit Code: 0

- **Windows Agent Test Suite:**
  - Command: `.venv\Scripts\pytest.exe agent/tests -v`
  - Total Passed: 49 / 49 passed
  - Execution Time: 56.41s
  - Exit Code: 0

### 4.2 Frontend Quality & Build Verification

- **Frontend Unit & Component Tests (Vitest):**
  - Command: `npm --prefix frontend test`
  - Total Test Files: 13 / 13 passed
  - Total Tests: 51 / 51 passed
  - Execution Time: 31.35s
  - Exit Code: 0
- **TypeScript Strict Compilation & Vite Build:**
  - Command: `npm --prefix frontend run build` (`tsc && vite build`)
  - Modules Transformed: 1748 modules
  - Result: Built successfully in 10.70s
  - Exit Code: 0
- **Frontend Linting (ESLint):**
  - Command: `npm --prefix frontend run lint` (`eslint src --max-warnings 0`)
  - Result: 0 warnings, 0 errors
  - Exit Code: 0
- **Frontend Production Docker Image:**
  - Command: `docker build -f frontend/Dockerfile . -t servicepulse-frontend:test`
  - Result: Built and tagged successfully
  - Exit Code: 0

### 4.3 Python Static Analysis & Migration Status

- **Ruff Linting:**
  - Command: `.venv\Scripts\ruff.exe check agent backend scripts tests`
  - Result: All checks passed (0 errors, 0 warnings).
  - Exit Code: 0
- **Alembic Migration Verification:**
  - Command: `docker compose exec backend alembic current`
  - Current Revision: `d5e6f7a8b9c0 (head)`
  - Exit Code: 0

### 4.4 Docker E2E Smoke Integration Test

- **Command:** `.venv\Scripts\python.exe backend/tests/smoke_docker_e2e.py`
- **Result:** 11 / 11 Scenarios Passed, 30 / 30 Verified Assertions, Exit Code: 0
- **Scenarios Verified:**
  - Scenario 1: Static & SPA Fallback Routes (Root, Live Monitoring, Analytics, Alert Center)
  - Scenario 2: Reverse Proxy Backend Health (`/api/v1/health` DB connected)
  - Scenario 3: Authentication via Reverse Proxy (Org 1 Admin, Org 2 User Provisioning)
  - Scenario 4: WebSocket Single-Use Ticket Issuance (Org 1 & 2 tickets, TTL: 30s)
  - Scenario 5: WebSocket Handshake & Bidirectional Ping/Pong Keepalive
  - Scenario 6: Separate Network Worker to WebSocket Delivery (Cross-tenant isolation & DB persistence)
  - Scenario 7: Event Deduplication & Worker Restart Recovery (Leadership regain & recovery probe)
  - Scenario 8: Disconnect Cleanup & Reconnection
  - Scenario 9: Security Guardrails & Ticket Invalidation (Reused, bogus, unauthenticated tickets rejected)
  - Scenario 10: End-to-End Docker Invitation Creation, Validation & Redemption through Nginx
  - Scenario 11: End-to-End Docker Organization Onboarding & Super Admin Approval through Nginx

---

## 5. Verification Matrix Summary

| Verification Target | Engine / Environment | Scope / Test Count | Result | Exit Code |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Auth & Registration** | Pytest / Docker PostgreSQL | 19 scenarios | PASSED | 0 |
| **Backend Full Regression** | Pytest / Docker PostgreSQL | 93 test scenarios | PASSED | 0 |
| **Windows Native Agent** | Pytest / Windows Host | 49 test scenarios | PASSED | 0 |
| **Frontend Tests** | Vitest / jsdom | 13 test files / 51 tests | PASSED | 0 |
| **TypeScript Strict Build** | `tsc` + Vite | 1748 modules | PASSED | 0 |
| **Frontend ESLint** | ESLint | 0 warnings, 0 errors | PASSED | 0 |
| **Python Code Quality** | Ruff | 全 codebase | PASSED | 0 |
| **Database Migration** | Alembic / PostgreSQL | Head `d5e6f7a8b9c0` | PASSED | 0 |
| **Frontend Docker Image** | Docker Engine | `servicepulse-frontend:test` | PASSED | 0 |
| **Docker E2E Smoke Test** | Python / Nginx Proxy | 11 scenarios / 30 assertions | PASSED | 0 |
