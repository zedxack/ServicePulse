#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Database Disaster Recovery & Restore Shell Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-backup.sql.gz> --container <container_name> [--force] [--confirm-production]"
    echo "Example: $0 backups/servicepulse_backup_20261114_120000.sql.gz --container sp-restore-test-db --force"
    exit 1
fi

ARCHIVE_PATH="$1"
shift

echo "Initiating ServicePulse disaster recovery restoration..."
python3 "${SCRIPT_DIR}/restore_db.py" --archive "${ARCHIVE_PATH}" "$@"
