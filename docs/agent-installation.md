# ServicePulse Native Windows Agent — Installation & Deployment Guide

**Author:** Muhammadyusuf Usmonov  
**Target Environment:** Enterprise IT Operations  
**Component:** Windows Agent Setup & Packaging  
**Target Platform:** Windows 11 / Windows 10 x64

---

## 1. Prerequisites

Before installing the agent on an endpoint, verify the following prerequisites:

| Requirement | Specification |
| :--- | :--- |
| **Operating System** | Windows 11 (22H2+) or Windows 10 (21H2+) 64-bit |
| **PowerShell** | PowerShell 5.1 or PowerShell 7+ |
| **Network** | TCP egress to ServicePulse backend server on configured port (e.g., 8000 or 443) |
| **Privileges** | Standard user privileges for running in console mode; Local Administrator elevation required for Windows Service installation (`sc.exe create`) |
| **Dependencies** | None required when using the standalone `ServicePulseAgent.exe` binary. Python 3.12+ required if running from source. |

---

## 2. Option A: Standalone Binary Deployment (Recommended)

The standalone single-file binary contains an embedded Python 3.12 runtime and all required native libraries (`pywin32`, `psutil`, `httpx`). It runs on endpoints **without Docker or Python installed**.

### Step 1: Compile or Obtain Binary
To compile the standalone binary from the repository on a build workstation:

```powershell
cd C:\Projects\ServicePulse
.venv\Scripts\python.exe agent\build_agent.py
```

The compiled executable is placed at:
```text
C:\Projects\ServicePulse\agent\dist\ServicePulseAgent.exe (~18 MB)
```

### Step 2: Deploy to Target Endpoint
Copy `ServicePulseAgent.exe` to a permanent location, e.g.:
```text
C:\Program Files\ServicePulse\ServicePulseAgent.exe
```

### Step 3: Enroll the Endpoint
Open an elevated PowerShell prompt and enroll the agent against the ServicePulse server:

```powershell
.\ServicePulseAgent.exe --enroll `
  --secret "<STRONG_ENROLLMENT_SECRET_FROM_ENV>" `
  --server-url "http://servicepulse.example.com:8000"
```

Output:
```text
SUCCESS: Agent enrolled successfully!
Agent UUID: agent_8db6a41e8def4d62
Device ID: 42
Credentials protected by Windows DPAPI: C:\ProgramData\ServicePulse\credentials.dat
```

### Step 4: Install and Start the Windows Service
```powershell
.\ServicePulseAgent.exe --install
.\ServicePulseAgent.exe --start
```

### Step 5: Verify Status
```powershell
.\ServicePulseAgent.exe --status
```

Expected output:
```text
=== ServicePulse Windows Agent Status ===
Agent Version:     1.0.0
Configured Server: http://servicepulse.example.com:8000
Agent Name:        LAB2-PC01
Enrolled:          YES
Agent UUID:        agent_8db6a41e8def4d62
Bound Device ID:   42
Organization ID:   1
Windows Service:   RUNNING
Service Installed: true
Queue DB Path:     C:\ProgramData\ServicePulse\telemetry_queue.db
```

---

## 3. Option B: Python Source Deployment (Development / Lab Mode)

### Step 1: Install Python Dependencies
```powershell
cd C:\Projects\ServicePulse\agent
pip install -r requirements.txt
```

### Step 2: Run in Console Mode for Debugging
```powershell
python servicepulse_agent.py --console --server-url "http://localhost:8000"
```

---

## 4. Uninstallation & Cleanup

To cleanly remove the ServicePulse Windows Agent:

```powershell
# 1. Stop the Windows Service
.\ServicePulseAgent.exe --stop

# 2. Uninstall from Windows Service Control Manager
.\ServicePulseAgent.exe --uninstall

# 3. Clean local data and credentials
Remove-Item -Recurse -Force "C:\ProgramData\ServicePulse"

# 4. Remove binary directory
Remove-Item -Recurse -Force "C:\Program Files\ServicePulse"
```
