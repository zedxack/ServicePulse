# ServicePulse API Specification (v1)

**Author:** Muhammadyusuf Usmonov  
**Base URL:** `/api/v1`  
**Authentication:** HTTP Bearer JWT / X-Agent-Token

---

## 1. Authentication & User Management (`/auth`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate user with Argon2id hash, issue JWT pair | Public |
| `POST` | `/api/v1/auth/refresh` | Single-use refresh token rotation | Public (valid refresh token) |
| `POST` | `/api/v1/auth/logout` | Revoke user active refresh tokens | Authenticated User |
| `GET` | `/api/v1/auth/me` | Retrieve profile and assigned roles of authenticated user | Authenticated User |
| `GET` | `/api/v1/auth/users` | List registered users (scoped to tenant unless Super Admin) | Admin, Support, Company Admin |
| `POST` | `/api/v1/auth/users` | Register a new user account | Super Admin, Company Admin |
| `PATCH` | `/api/v1/auth/users/{id}` | Update user details and roles | Super Admin, Company Admin |
| `PATCH` | `/api/v1/auth/users/{id}/status` | Activate or deactivate user | Super Admin, Company Admin |

---

## 2. Organization Management (`/organizations`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/organizations` | List all tenant organizations | Platform Super Admin |
| `POST` | `/api/v1/organizations` | Create a new tenant organization | Platform Super Admin |
| `GET` | `/api/v1/organizations/{id}` | Get organization details by ID | Super Admin or Tenant Admin |
| `PATCH` | `/api/v1/organizations/{id}` | Update organization details & quotas | Super Admin or Tenant Admin |

---

## 3. Five Role-Based Dashboards (`/dashboard`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/dashboard/platform` | Global health, multi-tenant asset stats, platform audits | Platform Super Admin |
| `GET` | `/api/v1/dashboard/company` | Tenant asset capacity, device quota utilization, org audits | Company Admin, Admin, Super Admin |
| `GET` | `/api/v1/dashboard/sysadmin` | Device status distribution, active incidents, telemetry averages | IT Admin, Support, Company Admin |
| `GET` | `/api/v1/dashboard/executive` | Infrastructure availability %, SLA achievement, MTTD/MTTR | Executive, Company Admin, IT Admin |
| `GET` | `/api/v1/dashboard/ceo` | Backward-compatibility alias for `/executive` | Executive, Company Admin, IT Admin |
| `GET` | `/api/v1/dashboard/employee` | Personal tickets, software requests, and approval status | Authenticated User |

---

## 4. Inventory Infrastructure (`/inventory`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/inventory/tree` | Complete organizational hierarchy tree | Authenticated User |
| `GET` | `/api/v1/inventory/buildings` | List registered buildings | Authenticated User |
| `POST` | `/api/v1/inventory/buildings` | Register a new building | Admin, Support, IT Admin |
| `GET` | `/api/v1/inventory/buildings/{id}` | Get building by ID | Authenticated User |
| `PATCH` | `/api/v1/inventory/buildings/{id}` | Update building details | Admin, Support, IT Admin |
| `DELETE` | `/api/v1/inventory/buildings/{id}` | Delete building (safeguarded against active devices) | Admin, Company Admin, Super Admin |
| `POST` | `/api/v1/inventory/floors` | Add a floor level to a building | Admin, Support, IT Admin |
| `POST` | `/api/v1/inventory/rooms` | Add a room to a floor | Admin, Support, IT Admin |
| `GET` | `/api/v1/inventory/devices` | List devices with filtering and pagination | Authenticated User |
| `POST` | `/api/v1/inventory/devices` | Register a new device | Admin, Support, IT Admin |
| `GET` | `/api/v1/inventory/devices/{id}` | Retrieve device details by ID | Authenticated User |
| `PATCH` | `/api/v1/inventory/devices/{id}` | Update device attributes | Admin, Support, IT Admin |
| `DELETE` | `/api/v1/inventory/devices/{id}` | Decommission/delete a device | Admin, Company Admin, Super Admin |

---

## 5. Incidents & Concurrency-Safe Deduplication (`/incidents`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/incidents` | List incidents with filtering and pagination | Authenticated User |
| `POST` | `/api/v1/incidents` | Create or concurrency-safely deduplicate incident | Authenticated User |
| `GET` | `/api/v1/incidents/{id}` | Retrieve incident with complete event audit trail | Authenticated User |
| `PATCH` | `/api/v1/incidents/{id}/assign` | Assign incident to a technician | Responders (IT Admin, Support, Admin) |
| `PATCH` | `/api/v1/incidents/{id}/acknowledge` | Acknowledge active incident | Responders (IT Admin, Support, Admin) |
| `PATCH` | `/api/v1/incidents/{id}/resolve` | Resolve incident and clear active deduplication key | Responders (IT Admin, Support, Admin) |

---

## 6. Remote Monitoring Agent Management (`/agent`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/agent/enroll` | Secure enrollment using enrollment secret | Pre-shared Secret Key |
| `POST` | `/api/v1/agent/heartbeat` | Agent keepalive heartbeat transmission | Enrolled Agent Token |
| `POST` | `/api/v1/agent/telemetry` | Idempotent system telemetry metrics ingestion | Enrolled Agent Token |

---

## 7. Helpdesk & Software Approval Workflow (`/tickets`, `/software`)

| Method | Endpoint | Description | Authorization |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/tickets` | Submit a new support ticket | Authenticated User |
| `GET` | `/api/v1/tickets` | List tickets (employee sees own; admin/support sees org) | Authenticated User |
| `GET` | `/api/v1/tickets/{id}` | Retrieve ticket by ID | Ticket Author or Admin/Support |
| `PATCH` | `/api/v1/tickets/{id}` | Update ticket metadata | Ticket Author or Admin/Support |
| `POST` | `/api/v1/tickets/{id}/comments` | Add comment to ticket discussion thread | Ticket Author or Admin/Support |
| `PATCH` | `/api/v1/tickets/{id}/assign` | Assign ticket to a technician | IT Admin, Support, Admin |
| `PATCH` | `/api/v1/tickets/{id}/resolve` | Mark ticket as resolved | IT Admin, Support, Admin |
| `POST` | `/api/v1/software/requests` | Submit software installation request | Authenticated User |
| `GET` | `/api/v1/software/requests` | List software requests | Authenticated User |
| `GET` | `/api/v1/software/requests/{id}` | Retrieve software request by ID | Request Author or Admin |
| `POST` | `/api/v1/software/requests/{id}/approve` | Approve request & dispatch agent command | Admin, Company Admin, IT Admin |
| `POST` | `/api/v1/software/requests/{id}/reject` | Reject software request with reason | Admin, Company Admin, IT Admin |
