# ServicePulse Database Architecture & Schema Specification

**Author:** Muhammadyusuf Usmonov  
**Database Engine:** PostgreSQL 16 (Production) / SQLite Async (Testing)  
**ORM:** SQLAlchemy 2.0 (Declarative Base with Mapped Columns)  
**Migration Tool:** Alembic

---

## 1. Entity Relationship Overview

The schema is normalized to 3NF, utilizing foreign keys, cascading rules, and composite indexes to ensure query performance and data integrity.

### Core Tables:

1. **Identity & Access Management:**
   - `users`: Authenticated operators and employees (`id`, `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser`, `last_login`, timestamps).
   - `roles`: Role definitions (`id`, `name`, `description`). Standard roles: `admin`, `support`, `employee`.
   - `permissions`: Granular capabilities (`id`, `code`, `name`, `description`).
   - `user_roles`: Many-to-many junction between users and roles.
   - `role_permissions`: Many-to-many junction between roles and permissions.

2. **Hierarchical Asset Inventory:**
   - `buildings`: Physical site records (`id`, `name`, `code`, `address`, `description`, `is_sample_data`).
   - `floors`: Building floor levels (`id`, `building_id`, `level`, `name`, `description`, `is_sample_data`).
   - `rooms`: Specific locations (`id`, `floor_id`, `room_number`, `name`, `description`, `is_sample_data`).
   - `devices`: Infrastructure endpoints (`id`, `room_id`, `name`, `hostname`, `ip_address`, `mac_address`, `device_type`, `operating_system`, `status`, `is_monitored`, `is_sample_data`, `consecutive_failures`, `last_seen`, `last_heartbeat`).

3. **Agent Management & Telemetry:**
   - `agents`: Registered client monitoring daemons (`id`, `device_id`, `agent_uuid`, `api_token_hash`, `status`, `version`, `hostname`, `ip_address`, `os_name`, `last_seen`).
   - `agent_telemetry`: Time-series system metrics (`id`, `agent_id`, `cpu_percent`, `ram_percent`, `ram_used_mb`, `ram_total_mb`, `disk_percent`, `disk_used_gb`, `disk_total_gb`, `windows_activation_status`, `windows_defender_status`, `recorded_at`).
   - `agent_commands`: Allowlisted dispatched actions (`id`, `agent_id`, `device_id`, `action_name`, `parameters`, `status`, `verification_status`, `execution_result`, `verification_result`, `requested_by_user_id`, timestamps).

4. **Network Monitoring & Incidents:**
   - `network_checks`: Network probe history (`id`, `device_id`, `check_type`, `port`, `is_successful`, `response_time_ms`, `packet_loss_percent`, `error_message`, `checked_at`).
   - `incidents`: Deduplicated incident records (`id`, `device_id`, `fingerprint`, `title`, `description`, `severity`, `status`, `occurrence_count`, `first_seen_at`, `last_seen_at`, `resolved_at`, `assigned_to_user_id`, `resolution_notes`).
   - `incident_events`: Audit trail for incident lifecycle events (`id`, `incident_id`, `event_type`, `message`, `payload`, `created_by_user_id`, `created_at`).

5. **Automated Remediation & ITSM:**
   - `remediation_rules`: Rule configuration (`id`, `name`, `description`, `trigger_condition`, `target_device_type`, `action_name`, `action_parameters`, `requires_approval`, `is_active`, `max_retries`, `cooldown_seconds`).
   - `remediation_executions`: Remediation log and independent verification (`id`, `rule_id`, `incident_id`, `device_id`, `status`, `verification_status`, `approved_by_user_id`, `execution_log`, `verification_log`, timestamps).
   - `tickets`: Employee helpdesk requests (`id`, `title`, `description`, `priority`, `status`, `author_id`, `assigned_to_id`, `device_id`).
   - `software_requests`: Software approval workflow (`id`, `user_id`, `device_id`, `software_name`, `software_version`, `reason`, `status`, `reviewed_by_user_id`, `review_notes`).
   - `audit_logs`: Append-only security audit log (`id`, `user_id`, `action`, `target_resource`, `target_id`, `status`, `details`, `ip_address`, `created_at`).

---

## 2. Migrations Workflow

Migrations are managed with Alembic.
To apply pending migrations:
```powershell
alembic -c backend/alembic.ini upgrade head
```
To generate a new migration after schema modification:
```powershell
alembic -c backend/alembic.ini revision --autogenerate -m "description_of_change"
```
