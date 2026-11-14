#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Production Deployment Automation Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# Target: Ubuntu 24.04 / 22.04 LTS VPS
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${ROOT_DIR}/compose.prod.yaml"
ENV_FILE="${ROOT_DIR}/.env.production"

echo "======================================================================"
echo " Starting ServicePulse Production Deployment Procedure"
echo " Author: Muhammadyusuf Usmonov | Academic Purpose: AT-Servis BMI"
echo "======================================================================"

# Step 1: Pre-flight Verification
echo "[1/6] Performing pre-flight checks..."
if [ ! -f "${ENV_FILE}" ]; then
    echo "Error: Production environment file ${ENV_FILE} not found!" >&2
    echo "Generate it first using: ./scripts/generate-secrets.sh" >&2
    exit 1
fi

# Verify secrets validity
python3 "${SCRIPT_DIR}/generate_secrets.py" --check "${ENV_FILE}"

# Step 2: Ensure Restrictive Permissions on Secrets
echo "[2/6] Enforcing file security permissions..."
chmod 600 "${ENV_FILE}"
mkdir -p "${ROOT_DIR}/backups"
chmod 700 "${ROOT_DIR}/backups"

# Step 3: Automated Pre-Deployment Safety Backup (if DB is already running)
echo "[3/6] Running pre-deployment safety backup..."
if docker ps --format '{{.Names}}' | grep -q "servicepulse-prod-db"; then
    python3 "${SCRIPT_DIR}/backup_db.py" --container servicepulse-prod-db --backup-dir "${ROOT_DIR}/backups" || {
        echo "Warning: Pre-deployment backup failed, but continuing..." >&2
    }
else
    echo "No running production database container detected; skipping safety dump."
fi

# Step 4: Build & Pull Container Images
echo "[4/6] Building production container images..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" build --pull

# Step 5: Start Services & Apply Database Migrations
echo "[5/6] Launching services in detached mode..."
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d

# Step 6: Post-Deployment Health & Smoke Verification
echo "[6/6] Verifying operational health..."
sleep 5

MAX_RETRIES=12
RETRY_COUNT=0
HEALTHY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Waiting for services to become healthy (attempt $((RETRY_COUNT+1))/${MAX_RETRIES})..."
    if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps | grep -q "(unhealthy)"; then
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT+1))
        continue
    fi
    
    # Check if backend and db are running
    if docker ps --format '{{.Names}} {{.Status}}' | grep "servicepulse-prod-backend" | grep -q "healthy"; then
        HEALTHY=true
        break
    fi
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ "$HEALTHY" = true ]; then
    echo "======================================================================"
    echo " ServicePulse Production Deployment COMPLETED SUCCESSFULLY!"
    echo " Domain: https://$(grep DOMAIN_NAME "${ENV_FILE}" | cut -d '=' -f2 | tr -d '\"')"
    echo "======================================================================"
else
    echo "Warning: Backend service has not reported healthy within expected timeframe." >&2
    echo "Inspect logs using: docker compose -f compose.prod.yaml logs" >&2
    exit 1
fi
