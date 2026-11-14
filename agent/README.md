# ServicePulse Native Windows Agent

**Author:** Muhammadyusuf Usmonov (AT-Servis BMI)  
**Version:** 1.0.0  
**Target:** Windows 11 / Windows 10 x64

---

## Quick Start

### 1. Run in Console Mode (Development & Testing)
```powershell
python servicepulse_agent.py --console --server-url "http://localhost:8000"
```

### 2. Enroll Agent with Backend
```powershell
python servicepulse_agent.py --enroll --secret "servicepulse-agent-enrollment-secret-2026" --server-url "http://localhost:8000"
```

### 3. Check Status
```powershell
python servicepulse_agent.py --status
```

### 4. Build Standalone Executable
```powershell
python build_agent.py
```
Output executable: `dist/ServicePulseAgent.exe` (~18 MB). Runs on any Windows 11 endpoint without Docker or Python installed!

### 5. Run Test Suite
```powershell
pytest tests/ -v
```

---

## Architecture Summary
- **Telemetry:** Genuine CPU, RAM, Fixed Disks, OS, Network, Windows Activation (CIM), Windows Defender (`Get-MpComputerStatus`).
- **Security:** Windows DPAPI token encryption, strict allowlist, `shell=False`, sensitive log redaction.
- **Resilience:** Crash-resilient SQLite WAL queue with exponential backoff synchronization.
- **Service:** Native Windows Service via `win32serviceutil.ServiceFramework` (`ServicePulseAgent`).
