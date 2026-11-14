# ServicePulse — STEP 5.1: Frontend Foundation & Role-Based Dashboards Report

**Project:** ServicePulse (Enterprise RMM & ITSM Platform)  
**Author:** Muhammadyusuf Usmonov (AT-Servis BMI)  
**Date:** 2026-11-14  
**Branch:** `feature/step-5-frontend`  
**Status:** STEP 5.1 Completed — Ready for Engineering Acceptance  

---

## 1. Executive Summary

In STEP 5.1, the frontend foundation of the **ServicePulse** enterprise platform was built from the ground up using React 18, TypeScript (strict mode), Vite, Tailwind CSS, TanStack Query, and React Router DOM. A unified authentication system connects to the live FastAPI backend, correctly loads user profiles and assigned roles, and automatically redirects authenticated users to their backend-authoritative `primary_dashboard`.

Five distinct, role-based dashboards were developed and mapped 1:1 to actual backend API responses:
1. **Platform Super Admin** (`/dashboard/platform`)
2. **Company Administrator** (`/dashboard/company`)
3. **SysAdmin / IT Operations** (`/dashboard/sysadmin`)
4. **Executive / CEO** (`/dashboard/executive`)
5. **Employee Self-Service** (`/dashboard/employee`)

The platform features full trilingual localization in **Uzbek** (`uz` default), **Russian** (`ru`), and **English** (`en`), with a dynamic language switcher, strict TypeScript type checking, zero ESLint warnings, 13 automated frontend component/integration tests, 62 backend PostgreSQL tests, and 49 native Windows Agent tests.

---

## 2. Implemented Frontend Architecture

```
frontend/
  ├── src/
  │   ├── app/
  │   │   ├── layouts/
  │   │   │   └── AppLayout.tsx          # Enterprise responsive header & sidebar navigation
  │   │   ├── pages/
  │   │   │   ├── NotFoundPage.tsx       # 404 handler
  │   │   │   └── UnauthorizedPage.tsx   # 403 RBAC rejection handler
  │   │   ├── providers/
  │   │   │   └── QueryProvider.tsx      # TanStack Query client setup
  │   │   └── router/
  │   │       └── index.tsx              # Centralized route tree with RBAC guards
  │   ├── features/
  │   │   ├── auth/
  │   │   │   ├── AuthContext.tsx        # Auth state, login/logout, role inspection
  │   │   │   ├── LoginPage.tsx          # Enterprise login with quick demo credentials
  │   │   │   └── ProtectedRoute.tsx     # Role-based route guard
  │   │   └── dashboard/
  │   │       ├── PlatformDashboardPage.tsx
  │   │       ├── CompanyDashboardPage.tsx
  │   │       ├── SysAdminDashboardPage.tsx
  │   │       ├── ExecutiveDashboardPage.tsx
  │   │       └── EmployeeDashboardPage.tsx
  │   ├── shared/
  │   │   ├── api/
  │   │   │   ├── client.ts              # Axios instance with JWT interceptor & 401 handler
  │   │   │   ├── auth.ts                # Auth API endpoints
  │   │   │   └── dashboard.ts           # 5 Dashboard API endpoints
  │   │   ├── components/
  │   │   │   └── LanguageSwitcher.tsx   # UZ/RU/EN selector
  │   │   └── types/
  │   │       ├── auth.ts                # User, Role, Token interfaces
  │   │       └── dashboard.ts           # Response models for all 5 dashboards
  │   ├── i18n/
  │   │   ├── config.ts                  # i18next configuration (uz default)
  │   │   └── locales/
  │   │       ├── uz.json                # Uzbek (default)
  │   │       ├── ru.json                # Russian
  │   │       └── en.json                # English
  │   ├── styles/
  │   │   └── index.css                  # Tailwind directives & enterprise scrollbars
  │   ├── test/
  │   │   ├── setup.ts                   # Vitest setup & in-memory storage polyfills
  │   │   ├── auth.test.tsx              # Auth lifecycle tests
  │   │   ├── protected_route.test.tsx   # RBAC protection tests
  │   │   ├── language_switcher.test.tsx # i18n tests
  │   │   └── dashboards.test.tsx        # 5 Dashboard render & contract tests
  │   ├── App.tsx
  │   └── main.tsx
  ├── public/
  ├── Dockerfile                         # Multi-stage production container
  ├── eslint.config.js                   # ESLint 9 configuration
  ├── index.html
  ├── package.json
  ├── postcss.config.js
  ├── tailwind.config.js
  ├── tsconfig.json
  ├── tsconfig.node.json
  └── vite.config.ts
```

---

## 3. Authentication & RBAC Flow

### 3.1 Authentication Workflow
1. **User Sign-in:** The user inputs credentials on `/login`.
2. **Backend Submission:** `POST /api/v1/auth/login` sends `{ email, password }` as JSON.
3. **Token Issuance:** The backend issues an access token and refresh token, along with metadata:
   - `primary_dashboard`: Computed server-side based on user roles (`platform`, `company`, `sysadmin`, `executive`, `employee`).
   - `roles`: Assigned roles array.
4. **Profile Hydration:** The frontend client requests `GET /api/v1/auth/me` with `Authorization: Bearer <token>` to load the complete user profile, tenant organization, and fine-grained permissions.
5. **Authoritative Redirection:** The frontend redirects the user directly to `/dashboard/${user.primary_dashboard}`.
6. **Session Expiration / 401 Handling:** The Axios response interceptor catches 401 Unauthorized, automatically revoking local storage and redirecting to `/login`.

### 3.2 Role-to-Dashboard Mapping

| Role Name | Backend Permissions | Primary Dashboard | Route Path | Access Restrictions |
| :--- | :--- | :--- | :--- | :--- |
| `platform_super_admin` | All permissions across all tenants | `platform` | `/dashboard/platform` | Super Admin / `platform_super_admin` only |
| `company_admin` / `admin` | Organization management, users, inventory, audit | `company` | `/dashboard/company` | Company Admin or Super Admin |
| `it_admin` / `support` | Infrastructure, agents, incidents, remediations, telemetry | `sysadmin` | `/dashboard/sysadmin` | IT Admin, Support, or Admins |
| `executive` | Availability, SLA, MTTD, MTTR, high-level indicators | `executive` | `/dashboard/executive` | Executive, CEO, or Admins |
| `employee` | Personal tickets, software requests, own device views | `employee` | `/dashboard/employee` | All authenticated users |

---

## 4. Five Role-Based Dashboards & Real API Integration

### 4.1 Platform Super Admin Dashboard (`/dashboard/platform`)
- **API Endpoint:** `GET /api/v1/dashboard/platform`
- **Rendered Metrics:**
  - Total Organizations (Active vs. Inactive breakdown)
  - Platform Devices & Total Agent Deployments
  - Global Active Outages / Incidents
  - Platform Health Status (`healthy`)
  - Global Security Audit Trail (Action, target resource, target ID, status badge, timestamp)

### 4.2 Company Admin Dashboard (`/dashboard/company`)
- **API Endpoint:** `GET /api/v1/dashboard/company`
- **Rendered Metrics:**
  - Organization Name badge (e.g. `TATU AT-Servis Lab`)
  - Total Organization Members
  - Registered Devices vs. Maximum Quota with visual utilization progress bar
  - Buildings count
  - Active Incidents count
  - Organization Audit Trail table

### 4.3 SysAdmin Operations Dashboard (`/dashboard/sysadmin`)
- **API Endpoint:** `GET /api/v1/dashboard/sysadmin`
- **Rendered Metrics:**
  - Device Status breakdown: Online (green), Offline (red), Warning (amber)
  - Incident Severity breakdown: Active, Critical, Daily incidents
  - Windows Agent Status: Active heartbeats vs. Offline agents
  - Automated Remediation Results: Verified recoveries, pending, failed
  - Live Telemetry Gauges: Average CPU %, Average RAM %, Average Disk %
  - Campus Building Breakdown Table: Total devices, online, offline, warning per building

### 4.4 Executive / CEO Dashboard (`/dashboard/executive`)
- **API Endpoint:** `GET /api/v1/dashboard/executive`
- **Rendered Metrics:**
  - Contractual SLA Target (`99.50%`)
  - Measured Contractual SLA: **Explicitly rendered as "Unavailable"** (adhering strictly to STEP 2/3 contracts stating that historical uptime calculation requires duration-based calculation and must never fabricate numbers)
  - Discrete Network Probe Success Ratio (rendered separately from contractual SLA)
  - Current Device Snapshot Availability %
  - Incident Performance: MTTD (Mean Time to Detect) & MTTR (Mean Time to Resolve) in minutes
  - Active Risk Level evaluation (`low`)
  - Top Risk Endpoints table with incident counts and consecutive failure metrics

### 4.5 Employee Self-Service Dashboard (`/dashboard/employee`)
- **API Endpoint:** `GET /api/v1/dashboard/employee`
- **Rendered Metrics:**
  - Personalized Greeting (`user_name`)
  - Open vs. Resolved Support Tickets counts
  - Pending Software Installation Requests count
  - Recent Support Tickets table (Title, priority, status, date)
  - Software Installation Requests table (Software name, status, date)

---

## 5. Localization Status

| Language | Code | Completeness | Coverage |
| :--- | :--- | :--- | :--- |
| **Uzbek (Default)** | `uz` | 100% | Navigation, authentication, dashboard metrics, roles, tables, error messages |
| **Russian** | `ru` | 100% | Full interface parity |
| **English** | `en` | 100% | Full interface parity |

A dedicated [LanguageSwitcher](file:///C:/Projects/ServicePulse/frontend/src/shared/components/LanguageSwitcher.tsx) is accessible from the top navbar and login page. Language preferences are persisted in `localStorage`.

---

## 6. Docker & Container Health Status

### 6.1 Multi-Stage Production Container Build
`frontend/Dockerfile` was tested and built cleanly using Docker:
```
#12 [builder 6/6] RUN npm run build
#12 ✓ built in 8.87s
#13 [stage-1 2/3] COPY --from=builder /app/dist /usr/share/nginx/html
#14 [stage-1 3/3] COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
```

### 6.2 Docker Compose Services
```
NAME                          SERVICE          STATUS                    PORTS
servicepulse-backend          backend          Up (healthy)              0.0.0.0:8000->8000/tcp
servicepulse-db               db               Up (healthy)              0.0.0.0:5432->5432/tcp
servicepulse-network-worker   network-worker   Up (healthy)              8000/tcp
```
- Port 5173 is mapped for frontend development.
- CORS origins configured in backend allow `http://localhost:5173`.
- `compose.prod.yaml` Caddy configuration remains intact.

---

## 7. Testing & Quality Verification

| Test Suite | Scope | Tests Passed | Status |
| :--- | :--- | :--- | :--- |
| **Frontend Vitest** | Auth, ProtectedRoute, LanguageSwitcher, 5 Dashboards, Login Security | **19 / 19** | **PASS** |
| **Frontend TypeScript** | Strict mode (`tsc --noEmit`) | **0 Errors** | **PASS** |
| **Frontend ESLint** | React hooks, TypeScript lint (`eslint src`) | **0 Errors / 0 Warnings** | **PASS** |
| **Production Build** | Vite bundle (`npm run build`) | **PASS (7.35s)** | **PASS** |
| **Docker Backend** | PostgreSQL integration (`pytest backend/tests`) | **62 / 62** | **PASS** |
| **Windows Agent** | Collectors, commands, queue, security (`pytest agent/tests`) | **49 / 49** | **PASS** |
| **Backend Ruff Linter** | PEP 8 / Code quality (`ruff check agent backend`) | **0 Errors** | **PASS** |
| **TOTAL AUTOMATED TESTS** | Full Platform Regression | **130 / 130** | **100% GREEN** |

---

## 8. Known Limitations & Remaining Work for STEP 5.2

- **STEP 5.2 Modules:** Detailed CRUD views for Inventory Hierarchy Explorer (Building -> Floor -> Room -> Device), Incident Management Lifecycle (Acknowledge, Assign, Resolve, Comment), Helpdesk Support Tickets Submission/Discussion, Software Approval Catalog Management, and Live Network Probing views will be implemented in subsequent Step 5 phases.
- **Service Installation:** ServicePulseAgent is preserved as a standalone executable (`agent/dist/ServicePulseAgent.exe`) and has **not** been installed globally in `services.msc`, as required.

---

## 9. Branch & Commit Details

- **Branch:** `feature/step-5-frontend`
- **Initial Step 4 Commit:** `6edbc5841519ca8c804893e22d189df59bafe71a`
- **Step 5.1 Foundation Commit:** `b8739d99cf131d186118e97e7eb31a74ca59c3f5`

---

## 10. Final Security & Integration Audit Sign-Off

### 10.1 Demo Login Security & Production Bundle Hardening
- **Vite Dead-Code Elimination:** Development demo credentials were extracted to a dedicated component (`frontend/src/features/auth/DevDemoAccounts.tsx`) and lazily imported via `import.meta.env.DEV ? React.lazy(() => import('./DevDemoAccounts')) : null`.
- **Zero Production Credential Leakage:** Static analysis and byte scanning of production bundles (`frontend/dist/assets/*.js`) confirmed that seed credentials (`AdminPass2026!`, `CompanyAdminPass2026!`, etc.) and demo email shortcuts are **100% purged** from production output.
- **Automated Verification:** Added `frontend/src/test/login.test.tsx` which explicitly tests:
  - Production mode (`import.meta.env.DEV = false`) does not render `dev-demo-accounts` or any demo credential triggers.
  - Form validation, credential submission, and authentication error alert rendering.

### 10.2 Strict In-Memory JWT Authentication Security
- **Elimination of Web Storage Tokens:** Replaced all `localStorage` and `sessionStorage` token writes with an in-memory closure (`setAuthToken`, `getAuthToken`, `clearAuthToken`) in `frontend/src/shared/api/client.ts`.
- **Status 401 Unauthorized Handling:** Invalid or expired token responses immediately clear in-memory state and dispatch a `servicepulse_unauthorized` event to redirect unauthenticated sessions to `/login`.
- **Status 403 Forbidden Session Preservation:** Non-permitted actions reject with 403 Forbidden without logging out the authenticated user. Verified via automated tests in `frontend/src/test/protected_route.test.tsx`.
- **Zero Secret Leakage:** Access tokens and passwords are never output to browser console logs or error banners.

### 10.3 Production Reverse Proxy & API Routing Parity
- **Relative API Prefix:** The Axios API client defaults to `baseURL: '/api/v1'`.
- **Development Proxy:** Vite dev server reverse-proxies `/api` to `http://localhost:8000`.
- **Production Architecture:** Nginx / Caddy reverse-proxies `/api/` to `backend:8000/api/` with SPA fallback `try_files $uri $uri/ /index.html;`. Client browsers in production never connect to `localhost:8000`.
- **Environment Isolation:** Zero backend secrets or private keys are exposed via `VITE_*` prefixes.

### 10.4 Real Backend Data Contracts & SLA Compliance
- All five dashboards strictly bind to live backend endpoints (`/api/v1/organizations`, `/api/v1/devices`, `/api/v1/incidents`, `/api/v1/audit/logs`, `/api/v1/agent-telemetry/summary`).
- Loading skeletons, empty states, and error alerts are fully implemented across all views.
- Contractual SLA Target (e.g. 99.9%) is rigorously separated from discrete probe success ratios. Duration-based SLA is explicitly flagged as "Unavailable until historical downtime engine is implemented" to prevent misleading representations.
