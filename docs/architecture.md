# ServicePulse Architecture Specification

**Author:** Muhammadyusuf Usmonov  
**Academic Purpose:** AT-Servis BMI  
**Version:** 2.0.0  
**Target Market:** Uzbekistan first, international expansion later.

---

## 1. System Overview

ServicePulse is an enterprise Remote Monitoring and Management (RMM) and IT Service Management (ITSM) platform structured around an autonomous, closed-loop operational lifecycle:

```
+-----------+      +------------+      +------------+      +------------+
|  MONITOR  | ---> |   DETECT   | ---> |  ANALYZE   | ---> |  CLASSIFY  |
+-----------+      +------------+      +------------+      +------------+
                                                                 |
+-----------+      +------------+      +------------+            v
|  RECORD   | <--- |   VERIFY   | <--- |  RESPOND   | <----------+
+-----------+      +------------+      +------------+
```

1. **MONITOR:** Periodic ICMP echo requests, TCP port probes (e.g., HTTP 80, HTTPS 443, RTSP 554, WinBox 8291), and native Windows Agent telemetry heartbeats.
2. **DETECT:** Network timeout, port connection failure, or abnormal system metrics (CPU > 90%, RAM > 95%, disk > 90%, missing agent heartbeat).
3. **ANALYZE:** Evaluation against threshold policies (e.g., 3 consecutive failed checks).
4. **CLASSIFY:** Tenant-isolated deduplication key calculation (`active_dedup_key = SHA256(org_id + device_id + title)`) to associate repeated events with the active incident or generate a new incident with severity (`critical`, `warning`, `info`).
5. **RESPOND:** Matching against allowlisted automated remediation rules. If sensitive, queues for administrator approval; if pre-approved, dispatches action.
6. **VERIFY:** Independent probe (re-pinging gateway, querying service status, or verifying socket response) to validate recovery.
7. **RECORD:** Permanent, append-only audit trail and incident event log for post-mortem analysis and SLA calculation.

---

## 2. Multi-Tenant Architecture

ServicePulse employs a shared-database, tenant-isolated multi-tenant architecture:

- **Tenant Entity:** The `Organization` model represents independent enterprise entities or university departments.
- **Scoping:** Resources (`Building`, `Device`, `Agent`, `Incident`, `Ticket`, `SoftwareRequest`, `RemediationRule`, `AuditLog`, `User`) are explicitly associated with an `organization_id`.
- **Query Scoping:** All API endpoints and service methods enforce scoping via `get_user_tenant_org_id(current_user)`.
- **Cross-Tenant Isolation:** Users assigned to Organization A can never query, enumerate, or modify resources belonging to Organization B. Cross-tenant lookups return `404 Not Found` to prevent entity existence enumeration.
- **Platform Super Admin:** Authorized platform administrators possess cross-organization visibility for global management, license quotas, and platform diagnostics.

---

## 3. Five Role-Based Dashboard Experiences

ServicePulse provides 5 tailored dashboard experiences matching organizational roles:

1. **Platform Super Admin (`/api/v1/dashboard/platform`):**
   - Global multi-tenant metrics (total organizations, active/inactive counts).
   - Platform-wide asset counts (users, devices, enrolled agents).
   - Global active incidents and system health indicator.
   - Global append-only security and administration audit log.

2. **Company Admin (`/api/v1/dashboard/company`):**
   - Organizational asset and user capacity.
   - Device utilization percent against licensed quota (`max_devices`).
   - Organizational infrastructure inventory summary and active incidents.
   - Organization-specific audit trail.

3. **SysAdmin / IT Support (`/api/v1/dashboard/sysadmin`):**
   - Real-time device status distribution (online, offline, warning, unknown).
   - Active and critical incident counts.
   - Agent connectivity health and offline agent alerts.
   - Building-by-building device health breakdown.
   - Aggregated system telemetry averages (CPU, RAM, disk usage).

4. **Executive / CEO (`/api/v1/dashboard/executive` and `/api/v1/dashboard/ceo`):**
   - Infrastructure availability percentage against SLA baseline (99.5%).
   - Mean Time to Detect (MTTD) and Mean Time to Remediate (MTTR) calculated from real incident history.
   - 7-day incident volume trends categorized by severity (`critical`, `warning`, `info`).
   - Top 5 high-risk devices ranked by incident recurrence and consecutive failure counts.
   - Real-time business impact executive summary.

5. **Employee Self-Service (`/api/v1/dashboard/employee`):**
   - Open and resolved personal helpdesk ticket counts.
   - Recent ticket discussion history and status updates.
   - Pending and approved software installation requests.

---

## 4. RBAC Roles & Fine-Grained Permissions

| Role Name | Scope | Key Capabilities |
| :--- | :--- | :--- |
| `platform_super_admin` | Global / Cross-tenant | Tenant creation, organization quotas, global user management, platform health. |
| `company_admin` | Organization | Manage tenant users, configure organization settings, view company analytics. |
| `it_admin` | Organization | Manage infrastructure inventory, incidents, remediation rules, agent commands. |
| `support` | Organization | Resolve incidents, manage tickets, inspect devices and agent telemetry. |
| `executive` | Organization | Read-only executive dashboards (SLA, MTTD, MTTR, business impact, trends). |
| `employee` | User self-service | Submit support tickets, track own tickets, request software installation. |

---

## 5. Independent Network Worker & Remediation Engine (Step 3)

The monitoring and remediation subsystem runs independently of the web API:

- **Network Worker Daemon (`backend/app/workers/network_worker.py`):** Runs as a standalone background service (`servicepulse-network-worker`).
- **Probe Engine (`backend/app/workers/probe_engine.py`):** Non-blocking ICMP ping subprocesses, TCP socket probes, and deterministic simulation adapters with microsecond latency measurement.
- **Incident & Outage Processor (`backend/app/workers/incident_processor.py`):** Manages consecutive failure thresholds (warning at 1, offline at threshold), maintains verified `OutageInterval` records, deduplicates incidents using tenant hashes, and executes automated recovery workflows upon probe success.
- **Automated Remediation Engine (`backend/app/services/remediation_service.py`):** Enforces strict allowlisting, parameter validation, cooldown windows, retry limits, and human-in-the-loop approval workflows before dispatching remediation commands.
- **Verification Service (`backend/app/services/remediation_verification.py`):** Validates post-remediation health through observable evidence, flagging simulation executions explicitly.

---

## 6. Duration-Based Historical Uptime Foundation

Unlike point-in-time snapshot ratios, contractual SLA uptime must be duration-based:

- **Verified Outage Intervals:** Downtime is measured by summing exact durations of closed and ongoing `OutageInterval` records within the observation window (e.g. 30 days).
- **Maintenance Window Exclusion:** Scheduled maintenance windows (`MaintenanceWindow`) are excluded from SLA downtime penalties if approved and active.
- **Insufficient Data Protection:** If historical probe observation count is insufficient for a statistically valid measurement, `uptime_status="insufficient_data"` is reported with `measured_uptime_percent=null` rather than misleading the user.

