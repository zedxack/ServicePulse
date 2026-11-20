#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Health Check Shell Wrapper
# Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
# Author: Muhammadyusuf Usmonov
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/check_health.py" "$@"
