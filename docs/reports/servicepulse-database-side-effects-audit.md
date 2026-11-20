# ServicePulse — Database Side-Effects & Audit Chronology Report

**Audit Date:** November 15, 2026  
**Auditor Roles:** Senior Backend Engineer, Database Reliability Auditor  
**System Identity:** ServicePulse Enterprise Hybrid RMM & ITSM Platform  
**Target Branch:** `feature/servicepulse-design-system`  
**Baseline Commit:** `ece18ab98e551b21b15367fa96c83a48cbee92ff`  
**Database Dialect:** PostgreSQL 16 Alpine (`servicepulse-db`)  
**Inspection Mode:** Strictly Read-Only (Zero `DELETE`, `TRUNCATE`, `DROP`, or modification operations)  

---

## 1. Executive Summary

During the independent design acceptance audit of ServicePulse, a read-only database inspection identified persistent records created in the development PostgreSQL database (`servicepulse-db`). These records were introduced across two activities:
1. **Interactive Screenshot Capture:** Creating minimal ticket data to capture populated operational states for the Helpdesk and Ticket Detail views.
2. **Automated Verification Suites:** Running live Agent integration tests and the multi-container Docker E2E smoke test against the running backend container.

This document records the exact chronology, record identifiers, relationships, and origin attribution for every side effect. The presence of these test records does not invalidate the design system elevation (which is verified as **PASS**), but highlights the need for isolated test database environments in future milestones.

---

## 2. Chronology of Events

All timestamps are verified from PostgreSQL record metadata and execution task logs:

| Phase | Verified UTC Timestamp | Description | Impact on Database |
| :--- | :--- | :--- | :--- |
| **Phase 1: Baseline Inspection** | `2026-11-15 06:45:00 UTC` | Initial read-only inspection of database state. Verified that `tickets` table contained `0` records and `incidents` table contained 15 records. | Read-Only (0 changes) |
| **Phase 2: Screenshot Fixture Generation** | `2026-11-15 06:50:08–06:51:38 UTC` | Creation of one support ticket and one internal comment via authenticated REST API to capture populated Helpdesk and Ticket Detail screenshots. | Created Ticket #1, Comment #1, AuditLogs #347–355 |
| **Phase 3: Agent Live Integration Tests** | `2026-11-15 07:02:37–07:03:01 UTC` | Execution of `pytest agent/tests -v`, specifically `test_live_backend_integration.py` connecting to live Docker backend. | Enrolled test Agents #89–92, created Software Request #21, AuditLogs #356–363 |
| **Phase 4: Docker Production E2E Smoke Test** | `2026-11-15 07:07:16–07:07:58 UTC` | Execution of `backend/tests/smoke_docker_e2e.py` testing 11 production scenarios against live reverse proxy and WebSocket stream. | Created Users #22–24, Org #6, OrgRequest #3, Invite #4, Incident #16, Notifications #15–16, AuditLogs #364–375 |
| **Phase 5: Final Read-Only Audit Inspection** | `2026-11-15 07:22:11–07:25:38 UTC` | Comprehensive read-only SQL queries to catalog and verify all created records and confirm device health. | Read-Only (0 changes) |

---

## 3. Detailed Side-Effect Record Inventory

### Category 1: Screenshot UI Fixtures
Created specifically to provide authentic, populated views for `audit_tickets_after.png`, `audit_tickets_after_light.png`, `audit_ticket_detail_after.png`, and `audit_ticket_detail_after_light.png`.

| Table | ID | Org ID | Created By | Created At (UTC) | Details & Relationships | Originating Activity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `tickets` | **1** | 1 | User #1 (`admin@servicepulse.uz`) | `2026-11-15 06:50:08.689111` | **Title:** `"VPN Gateway Authentication Timeout"`<br>**Description:** `"Multiple users in Building A are experiencing intermittent connection drops..."`<br>**Priority:** `high`, **Category:** `network`, **Status:** `open`<br>**Associated Device:** Device #1 (`srv-main-01`) | `POST /api/v1/tickets` (Screenshot setup) |
| `ticket_comments` | **1** | N/A | User #1 (`admin@servicepulse.uz`) | `2026-11-15 06:51:37.994707` | **Ticket ID:** 1<br>**Body:** `"Investigating IPSec phase-2 rekeying parameters on gateway SRV-MAIN-01."` | `POST /api/v1/tickets/1/comments` (Screenshot setup) |

### Category 2: Automated E2E Smoke Test Records
Created during the execution of `backend/tests/smoke_docker_e2e.py` verifying multi-tenant isolation, reverse proxy routing, and event streaming.

| Table | ID | Org ID | Created At (UTC) | Attributes & State | Originating Scenario |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `users` | **22** | 2 | `2026-11-15 07:07:16.998119` | Email: `tenant2_user_1794726436@uptime.uz`<br>Role: `company_admin` | Scenario 3 (Multi-tenant auth verification) |
| `users` | **23** | 1 | `2026-11-15 07:07:56.437083` | Email: `docker.user.26476@servicepulse.uz`<br>Role: `employee` | Scenario 10 (Invitation redemption test) |
| `users` | **24** | 6 | `2026-11-15 07:07:57.388859` | Email: `applicant.26476@dockercorp.uz`<br>Role: `company_admin` | Scenario 11 (Approved onboarding admin) |
| `organizations` | **6** | 6 | `2026-11-15 07:07:57.377544` | Name: `"Docker Test Corp 26476"`<br>Slug: `docker-corp-26476`<br>Domain: `dockercorp.uz`<br>Status: `is_active=True` | Scenario 11 (Onboarding tenant creation) |
| `organization_requests` | **3** | N/A | `2026-11-15 07:07:56.960188` | Org Name: `"Docker Test Corp 26476"`<br>Status: `approved`<br>Created Org ID: 6, Created User ID: 24 | Scenario 11 (Onboarding submission & approval) |
| `organization_invitations` | **4** | 1 | `2026-11-15 07:07:55.974313` | Prefix: `sp_inv_N5k82X`<br>Max Uses: 1, Uses Count: 1 (Exhausted) | Scenario 10 (Single-use invite validation) |
| `incidents` | **16** | 1 | `2026-11-15 07:07:26.686487` | Title: `"Device unreachable: SRV-MAIN-01 (192.168.10.10)"`<br>Severity: `critical`, Status: `resolved`<br>Device ID: 1 | Scenario 6 (Failure probe) & Scenario 7 (Recovery) |
| `incident_events` | **56–60** | 1 | `2026-11-15 07:07:26–07:07:54` | Lifecycle events for Incident #16: `detected`, `remediation_dispatched`, `deduplicated`, `recovery`, `resolved` | Scenarios 6 & 7 (Worker-to-WS delivery & deduplication) |
| `notifications` | **15** | 1 | `2026-11-15 07:07:42.040052` | Title: `"Device Offline: SRV-MAIN-01"`<br>Severity: `critical` | Scenario 6 (Monitoring worker status alert) |
| `notifications` | **16** | 1 | `2026-11-15 07:07:54.882721` | Title: `"Device Recovered: SRV-MAIN-01"`<br>Severity: `info` | Scenario 7 (Worker recovery alert) |

### Category 3: Agent Integration Test Records
Created during `pytest agent/tests -v` executing against the live Docker backend.

| Table | ID | Org ID | Created At (UTC) | Attributes & State | Originating Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `software_requests` | **21** | 1 | `2026-11-15 07:02:48.569269` | Software: `"7-Zip"`<br>Status: `approved`<br>User ID: 1 | `agent/tests/test_live_backend_integration.py` |
| `agents` | **89–92** | 1 | `2026-11-15 07:02:37–07:03:01` | Test agent enrollment sessions | `agent/tests/test_live_backend_integration.py` |

### Category 4: Historical State Transitions & Realtime Event Outbox
Generated dynamically by the background network monitoring worker during probe failure simulation and recovery:

| Table | ID(s) | Device ID | State Transition / Event | Timestamp (UTC) | Originating Activity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `device_state_transitions` | **33, 34** | 1 | `online -> offline` | `2026-11-15 07:07:26, 07:07:42` | Scenario 6 (Probe failure simulation) |
| `device_state_transitions` | **35** | 1 | `offline -> online` | `2026-11-15 07:07:54` | Scenario 7 (Probe recovery simulation) |
| `realtime_events` | **40, 41** | 1 | `device:status_change` | `2026-11-15 07:07:26, 07:07:42` | Outbox message queue for WebSocket broadcast |
| `realtime_events` | **42, 43** | 1 | `incident:resolved`, `device:status_change` | `2026-11-15 07:07:54` | Outbox message queue for WebSocket broadcast |

### Category 5: Append-Only Security Audit Trail
The immutable `audit_logs` table recorded all interactive logins and API operations:

| Audit Log IDs | Timestamp Range (UTC) | Actions Recorded |
| :--- | :--- | :--- |
| **347–355** | `2026-11-15 06:49:58–06:54:01` | `auth_login_success` for admin/support/executive/employee sessions; `ticket_created` for Ticket #1. |
| **356–363** | `2026-11-15 07:02:37–07:03:01` | `agent_enroll_unauthorized`, `agent_enrolled` (IDs 89–92), `software_request_submitted`, `software_request_approved` (ID 21). |
| **364–375** | `2026-11-15 07:07:16–07:07:57` | `user_created` (User #22), `incident_created` (Incident #16), `invitation_created` (ID 4), `user_registered_via_invitation` (User #23), `organization_request_submitted` (ID 3), `organization_request_approved` (Org #6, User #24). |

---

## 4. Current Fleet State & Integrity Assessment

At the conclusion of the audit (07:25:38 UTC), the device table was verified:
- **All 8 devices are in `online` status:**
  - `srv-main-01.servicepulse.local` (ID: 1): `online`
  - `gw-core.servicepulse.local` (ID: 2): `online`
  - `lab2-pc01.servicepulse.local` (ID: 3): `online`
  - `lab2-pc02.servicepulse.local` (ID: 4): `online`
  - `cam-kirish-01.servicepulse.local` (ID: 5): `online`
  - `cam-lab204-01.servicepulse.local` (ID: 6): `online`
  - `srv-uptime.local` (ID: 7): `online`
  - `sw-life.local` (ID: 8): `online`
- **Zero data loss or schema corruption:** No seed accounts, baseline devices, or existing configurations were modified or deleted.

---

## 5. Architectural Recommendation for Test Isolation

Currently, both `smoke_docker_e2e.py` and `agent/tests/test_live_backend_integration.py` connect directly to the active development database container (`servicepulse-db`).

### Recommended Isolation Pattern for Future Milestones:
1. **Dedicated Test Database (`servicepulse_test`):** Configure integration tests and E2E smoke tests to point to a distinct database instance or ephemeral PostgreSQL database created during the test lifecycle (`POSTGRES_DB=servicepulse_test`).
2. **Ephemeral Fixtures:** Use database transaction rollback or automated teardown hooks at the completion of E2E runs to clean up test tenants (`Docker Test Corp`), test users, and simulated incidents.
3. **Screenshot Seed Script:** Maintain a dedicated, idempotent screenshot seeding script that populates demo fixtures in a local sandbox rather than writing ad-hoc records to the shared database.
