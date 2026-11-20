# ==============================================================================
# ServicePulse - Production Secrets Generation PowerShell Script
# Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
# Author: Muhammadyusuf Usmonov
# ==============================================================================
param(
    [string]$TargetEnv = ".env.production"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "Generating cryptographically secure secrets for ServicePulse production..." -ForegroundColor Cyan

python "$ScriptDir\generate_secrets.py" --write "$RootDir\$TargetEnv" --template "$RootDir\infra\env\.env.production.template"
python "$ScriptDir\generate_secrets.py" --check "$RootDir\$TargetEnv"

Write-Host "Production secrets generation completed successfully." -ForegroundColor Green
