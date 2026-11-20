#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Database Backup Shell Script
# Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
# Author: Muhammadyusuf Usmonov
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BACKUP_DIR="${ROOT_DIR}/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

echo "Executing automated PostgreSQL backup for ServicePulse..."
python3 "${SCRIPT_DIR}/backup_db.py" \
    --compose-file "${ROOT_DIR}/compose.prod.yaml" \
    --backup-dir "${BACKUP_DIR}" \
    --retention-days "${RETENTION_DAYS}"

echo "ServicePulse backup routine completed."
