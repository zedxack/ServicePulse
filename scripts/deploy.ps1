# ==============================================================================
# ServicePulse - Production Deployment Automation PowerShell Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# ==============================================================================
param(
    [string]$EnvFile = ".env.production",
    [string]$ComposeFile = "compose.prod.yaml"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Starting ServicePulse Production Deployment Procedure" -ForegroundColor Cyan
Write-Host " Author: Muhammadyusuf Usmonov | Academic Purpose: AT-Servis BMI" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Pre-flight checks
if (-not (Test-Path "$RootDir\$EnvFile")) {
    Write-Error "Production environment file $RootDir\$EnvFile not found! Run scripts\generate-secrets.ps1 first."
}

python "$ScriptDir\generate_secrets.py" --check "$RootDir\$EnvFile"

# 2. Build images
Write-Host "Building production containers..." -ForegroundColor Cyan
docker compose --env-file "$RootDir\$EnvFile" -f "$RootDir\$ComposeFile" build

# 3. Start services
Write-Host "Launching services..." -ForegroundColor Cyan
docker compose --env-file "$RootDir\$EnvFile" -f "$RootDir\$ComposeFile" up -d

Write-Host "ServicePulse production containers launched." -ForegroundColor Green
