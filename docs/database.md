# ServicePulse Database Architecture & Schema Specification

**Author:** Muhammadyusuf Usmonov  
**Database Engine:** PostgreSQL 16 (Production / Docker) / SQLite Async (Testing)  
**ORM:** SQLAlchemy 2.0 (Declarative Base with Mapped Columns)  
**Migration Tool:** Alembic  
**Version:** 2.0.0

---

## 1. Entity Relationship Overview

The schema is normalized to 3NF, utilizing foreign keys, cascading rules, and indexes to ensure multi-tenant isolation, concurrency safety, and query performance.

### Core Tables:

1. **Multi-Tenant Organizations:**
   - `organizations`: Tenant metadata (`id`, `name`, `slug` [unique index], `domain`, `is_active`, `max_devices`, `created_at`, `updated_at`).

2. **Identity & Access Management:**
   - `users`: Authenticated operators and employees (`id`, `organization_id` [FK organizations.id, ON DELETE SET NULL], `email` [unique index], `hashed_password`, `full_name`, `is_active`, `is_superuser`, `last_login`, timestamps).
   - `roles`: Role definitions (`id`, `name` [unique], `description`). Roles: `platform_super_admin`, `company_admin`, `it_admin`, `support`, `executive`, `employee`, `admin`.
   - `permissions`: Granular capabilities (`id`, `code` [unique], `name`, `description`).
   - `user_roles`: Many-to-many junction between users and roles.
   - `role_permissions`: Many-to-many junction between roles and permissions.
   - `refresh_tokens`: Database-backed JWT refresh token tracking (`id`, `user_id` [FK users.id, ON DELETE CASCADE], `token_jti` [unique], `revoked`, `expires_at`, timestamps).

3. **Hierarchical Asset Inventory:**
   - `buildings`: Physical site records (`id`, `organization_id` [FK organizations.id], `name`, `code` [unique], `address`, `description`, `is_sample_data`, timestamps).
   - `floors`: Building floor levels (`id`, `building_id` [FK buildings.id], `level`, `name`, `description`, `is_sample_data`, timestamps).
   - `rooms`: Specific locations (`id`, `floor_id` [FK floors.id], `room_number`, `name`, `description`, `is_sample_data`, timestamps).
   - `devices`: Infrastructure endpoints (`id`, `organization_id` [FK organizations.id], `room_id` [FK rooms.id], `name`, `hostname`, `ip_address`, `mac_address`, `device_type`, `operating_system`, `status`, `is_monitored`, `is_sample_data`, `consecutive_failures`, `last_seen`, `last_heartbeat`, timestamps).

4. **Agent Management & Telemetry:**
   - `agents`: Registered client monitoring daemons (`id`, `organization_id` [FK organizations.id], `device_id` [FK devices.id], `agent_uuid` [unique], `api_token_hash` [unique index], `status`, `version`, `hostname`, `ip_address`, `os_name`, `last_seen`, timestamps).
   - `agent_telemetry`: Time-series system metrics (`id`, `agent_id` [FK agents.id], `cpu_percent`, `ram_percent`, `ram_used_mb`, `ram_total_mb`, `disk_percent`, `disk_used_gb`, `disk_total_gb`, `windows_activation_status`, `windows_defender_status`, `recorded_at`, `idempotency_key` [unique index]).
   - `agent_commands`: Allowlisted dispatched actions (`id`, `agent_id` [FK agents.id], `device_id` [FK devices.id], `action_name`, `parameters`, `status`, `verification_status`, `execution_result`, `verification_result`, `is_simulation`, `remediation_execution_id` [FK remediation_executions.id], `requested_by_user_id` [FK users.id], timestamps).

5. **Network Monitoring, Outages & Incidents (Step 3):**
   - `network_checks`: Network probe history (`id`, `device_id` [FK devices.id], `check_type`, `port`, `is_successful`, `response_time_ms`, `packet_loss_percent`, `error_message`, `checked_at`).
   - `device_monitoring_configs`: Per-device monitoring settings (`id`, `device_id` [FK devices.id, unique], `is_enabled`, `is_authorized`, `ping_enabled`, `tcp_ports`, `check_interval_seconds`, `timeout_seconds`, `consecutive_failure_threshold`, `simulation_mode`, timestamps).
   - `device_state_transitions`: Complete device state history (`id`, `device_id` [FK devices.id], `from_status`, `to_status`, `trigger_reason`, `consecutive_failures`, `transition_at`).
   - `outage_intervals`: Verified duration-based downtime records (`id`, `organization_id` [FK organizations.id], `device_id` [FK devices.id], `incident_id` [FK incidents.id], `started_at`, `ended_at`, `duration_seconds`, `is_planned`, `root_cause`, timestamps).
   - `maintenance_windows`: Scheduled maintenance periods for SLA exclusion (`id`, `organization_id` [FK organizations.id], `device_id` [FK devices.id], `title`, `description`, `start_time`, `end_time`, `is_active`, timestamps).
   - `incidents`: Deduplicated incident records (`id`, `organization_id` [FK organizations.id], `device_id` [FK devices.id], `fingerprint`, `active_dedup_key` [unique index while active, set to NULL on resolution], `title`, `description`, `severity`, `status`, `occurrence_count`, `first_seen_at`, `last_seen_at`, `resolved_at`, `assigned_to_user_id` [FK users.id], `resolution_notes`, timestamps).
   - `incident_events`: Audit trail for incident lifecycle events (`id`, `incident_id` [FK incidents.id], `event_type`, `message`, `payload`, `created_by_user_id` [FK users.id], `created_at`).

6. **Automated Remediation & ITSM:**
   - `remediation_rules`: Rule configuration (`id`, `organization_id` [FK organizations.id], `name`, `description`, `trigger_condition`, `target_device_type`, `action_name`, `action_parameters`, `requires_approval`, `is_active`, `max_retries`, `cooldown_seconds`, timestamps).
   - `remediation_executions`: Remediation log and independent verification (`id`, `rule_id` [FK remediation_rules.id], `incident_id` [FK incidents.id], `device_id` [FK devices.id], `agent_command_id` [FK agent_commands.id], `status`, `verification_status`, `is_simulation`, `retry_count`, `approved_by_user_id` [FK users.id], `execution_log`, `verification_log`, timestamps).
   - `tickets`: Employee helpdesk requests (`id`, `organization_id` [FK organizations.id], `title`, `description`, `category`, `priority`, `status`, `author_id` [FK users.id], `assigned_to_id` [FK users.id], `device_id` [FK devices.id], timestamps).
   - `ticket_comments`: Discussion threads on tickets (`id`, `ticket_id` [FK tickets.id], `author_id` [FK users.id], `comment`, timestamps).
   - `software_requests`: Software approval workflow (`id`, `organization_id` [FK organizations.id], `user_id` [FK users.id], `device_id` [FK devices.id], `software_name`, `software_version`, `reason`, `status`, `reviewed_by_user_id` [FK users.id], `review_notes`, `reviewed_at`, timestamps).
   - `audit_logs`: Append-only security audit log (`id`, `organization_id` [FK organizations.id], `user_id` [FK users.id], `action`, `target_resource`, `target_id`, `status`, `details`, `ip_address`, `created_at`).

---

## 2. Active Deduplication Mechanism

To prevent incident duplication races and duplicate alerts:
1. When an active incident is detected, `active_dedup_key` is set to `SHA256(org_id + device_id + title)`.
2. A unique database index enforces that only one open/in-progress incident with this key can exist at any given time.
3. Subsequent detections concurrency-safely lock and increment `occurrence_count` and update `last_seen_at`.
4. When resolved, `active_dedup_key` is updated to `None` (`NULL`). Because SQL standard allows multiple `NULL` values in a unique column, this frees the fingerprint so subsequent genuine failures create a fresh incident.

---

## 3. Migrations Workflow

Migrations are managed with Alembic.
```powershell
# Apply pending migrations locally
.\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head

# Apply pending migrations inside Docker PostgreSQL
docker compose exec backend alembic -c backend/alembic.ini upgrade head
```
