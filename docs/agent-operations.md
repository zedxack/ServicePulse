# ServicePulse Native Windows Agent — Operations & Administration Guide

**Author:** Muhammadyusuf Usmonov  
**Academic Purpose:** TATU AT-Servis BMI  
**Component:** Day-to-Day Administration & Troubleshooting  
**Target Platform:** Windows 11 / Windows 10 x64

---

## 1. Daily Operations & Service Management

### Service Control via Windows Commands
The agent service is named **`ServicePulseAgent`** and can be controlled via standard Windows administration tools:

```powershell
# Query status via PowerShell
Get-Service -Name ServicePulseAgent

# Query status via Command Line
sc.exe query ServicePulseAgent

# Restart service via PowerShell
Restart-Service -Name ServicePulseAgent

# Stop service
Stop-Service -Name ServicePulseAgent

# Start service
Start-Service -Name ServicePulseAgent
```

### Checking Agent Health via CLI
```powershell
.\ServicePulseAgent.exe --status
```

---

## 2. Configuration Reference

Configuration can be specified in `config.json` placed alongside the binary or in `C:\ProgramData\ServicePulse\config.json`.

```json
{
  "server_url": "http://localhost:8000",
  "agent_name": "LAB2-PC01",
  "heartbeat_interval_seconds": 30,
  "telemetry_interval_seconds": 60,
  "command_poll_interval_seconds": 15,
  "request_timeout_seconds": 10,
  "offline_queue_max_records": 10000,
  "log_level": "INFO",
  "verify_ssl": true,
  "data_dir": null,
  "ca_bundle_path": null
}
```

### Configuration Parameters:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `server_url` | string | `http://localhost:8000` | Base URL of ServicePulse backend |
| `agent_name` | string | Machine Hostname | Display name for the local endpoint |
| `heartbeat_interval_seconds` | integer | `30` | Interval between keepalive heartbeat pings |
| `telemetry_interval_seconds` | integer | `60` | Interval between full telemetry collections |
| `command_poll_interval_seconds`| integer | `15` | Interval between polling for pending commands |
| `request_timeout_seconds` | integer | `10` | HTTP request timeout |
| `offline_queue_max_records` | integer | `10000` | Maximum records in offline SQLite buffer |
| `log_level` | string | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `verify_ssl` | boolean | `true` | Enforce SSL/TLS certificate validation on HTTPS |

### Environment Variable Overrides:

Any setting can be overridden via environment variables without editing files:

- `SERVICEPULSE_SERVER_URL`
- `SERVICEPULSE_AGENT_NAME`
- `SERVICEPULSE_HEARTBEAT_INTERVAL`
- `SERVICEPULSE_TELEMETRY_INTERVAL`
- `SERVICEPULSE_COMMAND_POLL_INTERVAL`
- `SERVICEPULSE_REQUEST_TIMEOUT`
- `SERVICEPULSE_LOG_LEVEL`
- `SERVICEPULSE_DATA_DIR`

---

## 3. Log Locations & Log Rotation

Logs are written to:
```text
C:\ProgramData\ServicePulse\logs\servicepulse_agent.log
```

- **Rotation Policy:** Automatically rotates when file size reaches **10 MB**.
- **Retention:** Retains the 5 most recent rotated backups (`servicepulse_agent.log.1`, `...5`).
- **Data Protection:** All bearer tokens (`sp_tok_*`), enrollment secrets, and Windows product keys are automatically redacted by the logger.

To monitor live logs in real time:
```powershell
Get-Content -Path "C:\ProgramData\ServicePulse\logs\servicepulse_agent.log" -Wait -Tail 30
```

---

## 4. Troubleshooting Guide

### Issue 1: "Invalid agent enrollment secret"
- **Cause:** The `--secret` supplied does not match `AGENT_ENROLLMENT_SECRET` on the server.
- **Solution:** Verify the enrollment secret with the ServicePulse platform administrator. In development, the default secret is `servicepulse-agent-enrollment-secret-2026`.

### Issue 2: Agent reports "Server unreachable (offline mode active)"
- **Cause:** Network connectivity interrupted, backend server down, or firewall blocking egress.
- **Agent Behavior:** Telemetry continues collecting locally into `C:\ProgramData\ServicePulse\telemetry_queue.db`.
- **Solution:** Verify network route to server. Once connectivity is restored, the `QueueSyncWorker` automatically flushes all buffered records with exponential backoff.

### Issue 3: "Access is denied" during service installation
- **Cause:** Running in an unelevated standard user prompt.
- **Solution:** Right-click PowerShell or Command Prompt and select **"Run as Administrator"**, then re-run `.\ServicePulseAgent.exe --install`.

### Issue 4: "Cannot decrypt credentials" after machine migration
- **Cause:** Windows DPAPI encryption is bound to the original machine and user security context.
- **Solution:** Delete `C:\ProgramData\ServicePulse\credentials.dat` and re-run `--enroll`.
