# ServicePulse — Database Backup & Disaster Recovery Manual
**Enterprise Hybrid Remote Monitoring & Management (RMM) and IT Service Management (ITSM)**  
**Author:** Muhammadyusuf Usmonov  
**Academic Purpose:** Graduation Qualification Work (BMI), Tashkent University of Information Technologies (TUIT) & AT-Servis  
**Target Database:** PostgreSQL 16 Alpine

---

## 1. Backup Strategy & Objectives

| Objective | Target | Implementation Mechanism |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | $\le$ 24 hours (daily) / $\le$ 1 hour with WAL archiving | Automated daily `pg_dump` snapshots + transaction logs |
| **Recovery Time Objective (RTO)** | $\le$ 15 minutes | Streamed `psql` decompression and schema validation |
| **Integrity Assurance** | 100% Cryptographic Verification | SHA-256 checksums + JSON manifest metadata validation |
| **Retention Policy** | 7 Daily Backups (Configurable) | Automated pruning of expired archives via `backup_db.py` |

---

## 2. Backup Archive Structure

Each backup operation creates three immutable artifacts in the backup directory (`/opt/servicepulse/backups`):

```
backups/
├── servicepulse_backup_20261114_133750.sql.gz         # Gzip compressed database dump
├── servicepulse_backup_20261114_133750.sql.gz.sha256  # SHA-256 cryptographic checksum
└── servicepulse_backup_20261114_133750.meta.json      # Metadata manifest with schema revision
```

### Sample Metadata Manifest (`.meta.json`)
```json
{
  "backup_timestamp": "2026-11-14T13:37:51.102834+00:00",
  "database_name": "servicepulse",
  "database_user": "postgres",
  "container_source": "servicepulse-prod-db",
  "archive_filename": "servicepulse_backup_20261114_133750.sql.gz",
  "file_size_bytes": 200396,
  "sha256_checksum": "557d678fe4efd7a0b93e0f641cdaef33300cd497354ab25e318b7f34dddf9d0b",
  "alembic_revision": "c4d5e6f7a8b9",
  "servicepulse_version": "1.0.0",
  "author": "Muhammadyusuf Usmonov",
  "purpose": "AT-Servis BMI Production Backup"
}
```

---

## 3. Manual Backup Execution

### Linux VPS / Production
```bash
sudo bash /opt/servicepulse/scripts/backup-db.sh
```

### Cross-Platform Python Execution
```bash
python scripts/backup_db.py --compose-file compose.prod.yaml --backup-dir ./backups --retention-days 7
```

### Windows Development Execution
```powershell
.\scripts\backup-db.ps1 -BackupDir "backups" -RetentionDays 7
```

---

## 4. Automated Daily Backup Scheduling

### Option A: Systemd Timer (Recommended for Ubuntu VPS)

Create `/etc/systemd/system/servicepulse-backup.service`:
```ini
[Unit]
Description=ServicePulse PostgreSQL Automated Backup
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=root
WorkingDirectory=/opt/servicepulse
ExecStart=/bin/bash /opt/servicepulse/scripts/backup-db.sh
StandardOutput=journal
StandardError=journal
```

Create `/etc/systemd/system/servicepulse-backup.timer`:
```ini
[Unit]
Description=Daily ServicePulse PostgreSQL Backup Trigger

[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and activate:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now servicepulse-backup.timer
sudo systemctl list-timers --all | grep servicepulse
```

### Option B: Linux Crontab
```bash
0 3 * * * /bin/bash /opt/servicepulse/scripts/backup-db.sh >> /var/log/servicepulse-backup.log 2>&1
```

---

## 5. Restoration Procedure

### 5.1 Verification Prior to Restore
Always verify backup integrity before initiating a restoration:
```bash
python scripts/restore_db.py --archive backups/servicepulse_backup_20261114_133750.sql.gz --verify-only
```

### 5.2 Restoring to Production Database
```bash
sudo bash scripts/restore-db.sh backups/servicepulse_backup_20261114_133750.sql.gz
```
The script:
1. Re-validates the SHA-256 checksum against `.sha256` and `.meta.json`.
2. Asks for operator confirmation.
3. Gracefully terminates competing active database connections.
4. Streams decompressed SQL into PostgreSQL via `psql`.
5. Queries and confirms all tables (`users`, `organizations`, `devices`, `incidents`, `tickets`, `notifications`, `realtime_events`).
6. Confirms Alembic migration revision matches head (`c4d5e6f7a8b9`).

### 5.3 Safe Disaster Recovery Test (Disposable Container)
Verify a backup without touching or disrupting production:
```bash
pytest tests/test_disaster_recovery.py -v
```
This test spins up an isolated ephemeral PostgreSQL container, restores the archive, asserts table row counts and Alembic version, and cleans up completely.
