# ==============================================================================
# ServicePulse - Database Backup PowerShell Script
# Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
# Author: Muhammadyusuf Usmonov
# ==============================================================================
param(
    [string]$BackupDir = "backups",
    [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "Executing ServicePulse PostgreSQL database backup..." -ForegroundColor Cyan

python "$ScriptDir\backup_db.py" `
    --backup-dir "$RootDir\$BackupDir" `
    --retention-days $RetentionDays

Write-Host "ServicePulse backup routine completed successfully." -ForegroundColor Green
