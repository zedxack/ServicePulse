# ServicePulse — Secure Authentication, Registration & Organization Onboarding Architecture

**Author:** Muhammadyusuf Usmonov  
**Target Environment:** Enterprise IT Operations  
**System Identity:** ServicePulse Enterprise Hybrid RMM & ITSM Platform  
**Document Version:** 1.0.0  
**Status:** Accepted & Production-Ready  

---

## 1. Executive Summary & Design Philosophy

ServicePulse provides an enterprise-grade multi-tenant architecture designed to eliminate unauthorized self-registration, privilege escalation, cross-tenant data leaks, and token harvesting vulnerabilities.

In traditional open-registration SaaS applications, arbitrary users can create accounts and assign arbitrary organizations or roles. ServicePulse adheres to strict enterprise security principles:

1. **No Open / Arbitrary Self-Registration:** Users cannot arbitrarily join organizations without an explicit, time-limited, cryptographic invitation issued by an authorized administrator.
2. **Onboarding Requests Require Platform Super Admin Approval:** An applicant representing a new tenant organization submits an onboarding request. This creates a `pending` state; it never grants immediate login privileges or provisions tenant resources until approved by a Platform Super Administrator.
3. **Cryptographic Token Protection (Hash at Rest):** Invitation tokens are high-entropy, cryptographically random strings (`sp_inv_<urlsafe_24>`). Raw tokens are returned to administrators once at creation time; only their SHA-256 digests (`token_hash`) are persisted in the database.
4. **Concurrency-Safe Atomic Redemption:** Invitation usage limits (`max_uses`, `uses_count`) are guarded using PostgreSQL pessimistic row-level locking (`SELECT ... FOR UPDATE`), preventing race conditions and usage exhaustion bypass.
5. **Role Escalation Prevention:** Role assignment is strictly bounded. Company administrators can only invite users to roles permitted within their tenant (`employee`, `support`, `it_admin`, `executive`). They cannot grant `platform_super_admin` or `company_admin` roles.
6. **Pure In-Memory JWT Architecture:** Client-side access tokens are kept exclusively in memory within React state (`AuthContext.tsx`). Neither `localStorage` nor `sessionStorage` is ever used for bearer tokens, mitigating Cross-Site Scripting (XSS) token harvesting.
7. **Transparent Email Provider Abstraction:** Outbound email uses an extensible provider pattern (`EmailProvider`, `SMTPEmailProvider`, `NullEmailProvider`). In environments without an SMTP server, the system transparently logs the operation without pretending delivery or leaking raw credentials.

---

## 2. Onboarding & Registration Workflows

### 2.1 Workflow A: Join Existing Organization (Invitation-Based)

```
[ Company Admin / Super Admin ]
               │
               ▼
      POST /api/v1/auth/invitations
               │
               ├─ Verify Role Escalation Guardrails (Tenant scoped)
               ├─ Generate raw_token = sp_inv_<random24>
               ├─ Compute token_hash = SHA256(raw_token)
               ├─ Persist OrganizationInvitation (hash only)
               └─ Return raw_token once to admin
               │
               ▼
[ New Employee / Engineer Receives Token ]
               │
               ▼
      POST /api/v1/auth/invitations/validate
               │
               ├─ Hash input code & query DB
               ├─ Check expiration, revocation, uses_count < max_uses
               └─ Return organization name & assigned role
               │
               ▼
      POST /api/v1/auth/join-organization
               │
               ├─ Validate Password Complexity (8+ chars, upper, lower, digit, special)
               ├─ Verify email uniqueness
               ├─ BEGIN TRANSACTION
               ├─ SELECT ... FOR UPDATE (Row Lock on invitation)
               ├─ Verify: not revoked, not expired, uses_count < max_uses
               ├─ Increment uses_count += 1
               ├─ Create User with assigned Role & Organization
               ├─ Write AuditLog (user_registered_via_invitation)
               ├─ COMMIT TRANSACTION
               └─ Return JWT Token Pair (In-Memory Sign In)
```

### 2.2 Workflow B: Register New Organization (Pending Platform Approval)

```
[ Organization Applicant / Representative ]
               │
               ▼
      POST /api/v1/auth/organization-requests
               │
               ├─ Validate corporate email & candidate slug
               ├─ Validate administrator password complexity
               ├─ Hash password with Argon2id
               ├─ Persist OrganizationRequest (status = 'pending')
               ├─ Write AuditLog (organization_request_submitted)
               ├─ Dispatch notification to applicant via EmailProvider
               └─ Return 201 Created (status: 'pending')
               │
               ▼ (Zero immediate access granted to applicant)
               │
[ Platform Super Administrator ]
               │
               ▼
      GET /api/v1/platform/organization-requests?status=pending
               │
               ▼
      POST /api/v1/platform/organization-requests/{id}/approve
               │
               ├─ BEGIN TRANSACTION
               ├─ Create Organization (name, slug, is_active=True)
               ├─ Fetch system 'company_admin' Role
               ├─ Create initial Administrator User (is_active=True, role=company_admin)
               ├─ Update OrganizationRequest (status='approved', created_org_id, created_user_id)
               ├─ Write AuditLog (organization_request_approved)
               ├─ COMMIT TRANSACTION
               └─ Dispatch approval notification email
               │
               ▼
[ Applicant Can Now Log In as Company Admin ]
```

---

## 3. Cryptographic Storage & Concurrency Guarantees

### 3.1 Invitation Token Hashing & Prefixing

| Component | Example Value | Description |
| :--- | :--- | :--- |
| **Raw Token** | `sp_inv_xK89_2wP01LzM...` | 24-byte high-entropy URL-safe secret returned once to creator. |
| **Token Prefix** | `sp_inv_xK89` | First 13 characters kept in cleartext for admin listing and audit trails. |
| **Token Hash** | `e3b0c44298fc1c149afb...` | Hexadecimal SHA-256 digest stored as unique indexed column `token_hash`. |

### 3.2 Row-Level Locking (`with_for_update()`)

To ensure usage limits cannot be bypassed by concurrent redemption requests, the redemption service executes within an explicit transaction with pessimistic locking:

```python
stmt = (
    select(OrganizationInvitation)
    .where(OrganizationInvitation.token_hash == token_hash)
    .with_for_update()
)
invitation = (await db.execute(stmt)).scalar_one_or_none()
```

If multiple threads or requests attempt to redeem the final remaining use simultaneously:
1. The first transaction obtains an exclusive row lock.
2. The second transaction blocks until the first completes.
3. Once the first commits (`uses_count` incremented to `max_uses`), the second wakes up, re-evaluates `uses_count >= max_uses`, and immediately raises `HTTP 400 Bad Request` ("This invitation has reached its maximum allowed uses").

---

## 4. API Endpoints Reference

### 4.1 Public & Authentication Endpoints (`/api/v1/auth`)

| Method | Endpoint | Access | Description | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Public | Authenticate user, issue in-memory JWT access & refresh tokens | 15 req/min |
| `POST` | `/auth/refresh` | Public | Rotate refresh token and issue new JWT pair | 15 req/min |
| `POST` | `/auth/logout` | Authenticated | Revoke user active refresh tokens | Normal |
| `GET` | `/auth/me` | Authenticated | Retrieve authenticated user profile, roles, and permissions | Normal |
| `POST` | `/auth/join-organization` | Public | Redeem valid invitation code, create user, return auth tokens | 5 req/min |
| `POST` | `/auth/invitations/validate` | Public | Check invitation validity, return org name and role | 15 req/min |
| `POST` | `/auth/organization-requests` | Public | Submit new organization onboarding request (status: pending) | 5 req/min |
| `POST` | `/auth/invitations` | Admins | Generate time-limited invitation for the organization | Normal |
| `GET` | `/auth/invitations` | Admins | List invitations for user's organization | Normal |
| `DELETE` | `/auth/invitations/{id}` | Admins | Revoke active invitation | Normal |

### 4.2 Platform Administration Endpoints (`/api/v1/platform`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/platform/organization-requests` | Super Admin | List all onboarding requests (filterable by status) |
| `GET` | `/platform/organization-requests/{id}` | Super Admin | Get details of a specific onboarding request |
| `POST` | `/platform/organization-requests/{id}/approve` | Super Admin | Approve request, provision organization and company admin |
| `POST` | `/platform/organization-requests/{id}/reject` | Super Admin | Reject request with recorded reason and notification |

---

## 5. Security & Isolation Matrix

| Threat Vector | Mitigation Strategy | Verification Result |
| :--- | :--- | :--- |
| **Token Harvesting (XSS)** | Pure in-memory JWT storage; access tokens never written to `localStorage` / `sessionStorage`. | Verified by unit & E2E tests |
| **Token Database Leakage** | Tokens stored as SHA-256 hashes; stolen database dump cannot reveal plaintext tokens. | Verified by schema inspection |
| **Privilege Escalation** | Company admins forbidden from assigning `platform_super_admin` or `company_admin`. | Verified by scenario 4 test |
| **Concurrent Exhaustion** | Atomic `with_for_update()` locking prevents multiple users redeeming single-use invites. | Verified by scenario 8 test |
| **Cross-Tenant Invitation** | Company admins restricted strictly to their authenticated tenant `organization_id`. | Verified by scenario 3 & 9 tests |
| **Weak Passwords** | Enforced 8+ length, uppercase, lowercase, numbers, and special symbols. | Verified by scenario 10 test |
| **Spam / DoS on Auth** | Sliding window in-memory rate limiter per client IP. | Verified by rate limiter tests |
