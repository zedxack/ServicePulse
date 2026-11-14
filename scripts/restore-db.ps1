# ==============================================================================
# ServicePulse - Database Restore PowerShell Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# ==============================================================================
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ArchivePath,

    [Parameter(Mandatory=$true)]
    [string]$Container,

    [string]$DbName = "servicepulse",
    [string]$DbUser = "postgres",
    [switch]$Force,
    [switch]$ConfirmProduction,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$params = @(
    "$ScriptDir\restore_db.py",
    "--archive", $ArchivePath
)

if ($VerifyOnly) {
    $params += "--verify-only"
} else {
    $params += @("--container", $Container, "--db-name", $DbName, "--db-user", $DbUser)
    if ($Force) { $params += "--force" }
    if ($ConfirmProduction) { $params += "--confirm-production" }
}

Write-Host "Initiating ServicePulse disaster recovery restoration..." -ForegroundColor Cyan
python @params
