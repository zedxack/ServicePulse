#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Production Secrets Generation Shell Wrapper
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET_ENV="${1:-.env.production}"

echo "Generating cryptographically secure secrets for ServicePulse production..."
python3 "${SCRIPT_DIR}/generate_secrets.py" --write "${ROOT_DIR}/${TARGET_ENV}" --template "${ROOT_DIR}/infra/env/.env.production.template"

if [ -f "${ROOT_DIR}/${TARGET_ENV}" ]; then
    chmod 600 "${ROOT_DIR}/${TARGET_ENV}"
    echo "Permissions set to chmod 600 on ${ROOT_DIR}/${TARGET_ENV}"
fi

python3 "${SCRIPT_DIR}/generate_secrets.py" --check "${ROOT_DIR}/${TARGET_ENV}"
echo "Production secrets generation completed successfully."
