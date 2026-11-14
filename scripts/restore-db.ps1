# ==============================================================================
# ServicePulse - Database Restore PowerShell Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# ==============================================================================
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ArchivePath,

    [string]$Container = "servicepulse-db",
    [switch]$Force,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$params = @(
    "$ScriptDir\restore_db.py",
    "--archive", $ArchivePath,
    "--container", $Container
)

if ($Force) { $params += "--force" }
if ($VerifyOnly) { $params += "--verify-only" }

Write-Host "Initiating ServicePulse disaster recovery restoration..." -ForegroundColor Cyan
python @params
