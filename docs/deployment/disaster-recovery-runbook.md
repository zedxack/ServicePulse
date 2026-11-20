# ServicePulse — Disaster Recovery Runbook
**Enterprise Hybrid Remote Monitoring & Management (RMM) and IT Service Management (ITSM)**  
**Author:** Muhammadyusuf Usmonov  
**Target Environment:** Enterprise Production Operations  
**Target Environment:** Ubuntu 24.04 / 22.04 LTS VPS | PostgreSQL 16 Alpine

---

## 1. Incident Severity Matrix

| Severity | Definition | Target RTO | Target RPO | Escalation Path |
| :--- | :--- | :--- | :--- | :--- |
| **P1 - Critical** | Platform down; web UI and API unreachable; monitoring halted. | $\le$ 30 min | $\le$ 24 hrs | System Administrator & Author |
| **P2 - Major** | Core feature impaired (e.g., WebSocket notifications down, network probes stalled). | $\le$ 2 hrs | N/A | DevOps Lead |
| **P3 - Moderate** | Single device agent offline; cosmetic dashboard error; non-blocking API fault. | $\le$ 8 hrs | N/A | Support Engineer |
| **P4 - Minor** | Minor UI defect; non-critical log warning. | Next release | N/A | Development Team |

---

## 2. Emergency Recovery Scenarios

### Scenario A: Complete Host Failure (VPS Rebuild from Scratch)
**Trigger:** VPS provider hardware fault, disk failure, or server destruction.

```bash
# 1. Provision new Ubuntu 24.04 LTS VPS with the same IP or update DNS A record
# 2. Log in as root via SSH
ssh root@<NEW_VPS_IP>

# 3. Clone ServicePulse repository
git clone https://github.com/Muhammadyusuf0807/ServicePulse.git /opt/servicepulse
cd /opt/servicepulse

# 4. Run automated server hardening
sudo bash scripts/harden-server.sh 22

# 5. Restore production environment secrets from secure offline vault
cat << 'EOF' > .env.production
# Paste verified offline backup of .env.production
EOF
chmod 600 .env.production

# 6. Copy latest verified backup archive to /opt/servicepulse/backups/
scp user@backup-server:servicepulse_backup_LATEST.sql.gz* /opt/servicepulse/backups/

# 7. Start database container only
docker compose -f compose.prod.yaml up -d db
sleep 10

# 8. Restore database from backup
bash scripts/restore-db.sh backups/servicepulse_backup_LATEST.sql.gz --force

# 9. Launch full production application stack
bash scripts/deploy.sh

# 10. Verify full operational readiness
python3 scripts/check_health.py
```

---

### Scenario B: Database Corruption or Accidental Data Deletion
**Trigger:** Corrupted disk block, operator error (`DROP TABLE`), or malicious tampering.

```bash
cd /opt/servicepulse

# 1. Stop application and worker services to prevent further database writes
docker compose -f compose.prod.yaml stop backend network-worker frontend

# 2. Verify integrity of the target backup archive
python3 scripts/restore_db.py --archive backups/servicepulse_backup_LATEST.sql.gz --verify-only

# 3. Restore the verified snapshot
sudo bash scripts/restore-db.sh backups/servicepulse_backup_LATEST.sql.gz --force

# 4. Verify database schema and Alembic revision
docker compose -f compose.prod.yaml exec db psql -U postgres -d servicepulse -c "SELECT version_num FROM alembic_version;"

# 5. Restart all application services
docker compose -f compose.prod.yaml up -d

# 6. Run operational health telemetry
python3 scripts/check_health.py
```

---

### Scenario C: Docker Container Crash Loop (OOM / Bug)
**Trigger:** Container repeatedly crashes and restarts (`Restarting (1)` status).

```bash
cd /opt/servicepulse

# 1. Identify failing container
docker compose -f compose.prod.yaml ps

# 2. Inspect container termination reasons and error logs
docker compose -f compose.prod.yaml logs --tail=100 backend

# 3. If Out-Of-Memory (OOM killed):
# Inspect exit code 137 in docker inspect
docker inspect servicepulse-prod-backend --format='{{.State.ExitCode}} {{.State.OOMKilled}}'

# 4. Adjust memory limits in compose.prod.yaml if necessary:
# limits:
#   memory: 2048M

# 5. Restart specific service
docker compose -f compose.prod.yaml up -d --no-deps backend
```

---

### Scenario D: Compromised Production Secrets (Credential Breach)
**Trigger:** Accidental leak of `SECRET_KEY`, `AGENT_ENROLLMENT_SECRET`, or `POSTGRES_PASSWORD`.

```bash
cd /opt/servicepulse

# 1. Generate new cryptographically secure secrets
python3 scripts/generate_secrets.py --write .env.production.new

# 2. Rotate Database Password in PostgreSQL:
NEW_PG_PASS=$(grep POSTGRES_PASSWORD .env.production.new | cut -d '=' -f2 | tr -d '\"')
docker compose -f compose.prod.yaml exec db psql -U postgres -c "ALTER USER servicepulse_admin WITH PASSWORD '${NEW_PG_PASS}';"

# 3. Replace .env.production
mv .env.production.new .env.production
chmod 600 .env.production

# 4. Recreate backend and worker containers to consume new secrets
docker compose -f compose.prod.yaml up -d --force-recreate backend network-worker

# 5. Invalidate existing active JWT sessions by restarting backend
# 6. Issue updated enrollment secret to Windows Agent administrators
```

---

### Scenario E: Caddy TLS Certificate Failure or ACME Rate Limiting
**Trigger:** Caddy fails to renew Let's Encrypt certificate or hits rate limits.

```bash
cd /opt/servicepulse

# 1. Inspect Caddy certificate logs
docker compose -f compose.prod.yaml logs caddy | grep -i "certificate"

# 2. Verify port 80 is not blocked by external firewall or ISP
curl -I http://servicepulse.uz/.well-known/acme-challenge/test

# 3. Force Caddy certificate reload
docker compose -f compose.prod.yaml exec caddy caddy reload --config /etc/caddy/Caddyfile

# 4. Emergency fallback to internal self-signed TLS (temporary)
# Add "tls internal" to Caddyfile and reload
```

---

## 3. Post-Incident Review (PIR) Template

Following resolution of any P1 or P2 incident, complete the following within 24 hours:

```markdown
# ServicePulse Post-Incident Review (PIR)
- **Incident ID:** INC-YYYYMMDD-01
- **Severity Level:** P1 / P2
- **Lead Investigator:** Muhammadyusuf Usmonov
- **Outage Duration:** XX minutes (Start: UTC, End: UTC)
- **Root Cause Analysis (5 Whys):**
- **Immediate Corrective Actions Taken:**
- **Preventative Measures to Avoid Recurrence:**
- **RTO / RPO Achieved:** RTO: XX min, RPO: XX min
```
