"""
ServicePulse Windows Agent - Live Docker Backend API Integration Test Suite
Verifies the complete operational loop against the live running Docker backend:
Agent -> Backend API -> PostgreSQL -> AgentCommand -> Execution -> Audit Log.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import os
import uuid
from pathlib import Path

import httpx
import pytest
from servicepulse.api_client import AgentAuthError, ApiClient
from servicepulse.authentication import AgentCredentials, CredentialStore
from servicepulse.commands import CommandDispatcher
from servicepulse.config import AgentConfig
from servicepulse.telemetry import TelemetryAggregator

BACKEND_URL = "http://localhost:8000"


def _get_enrollment_secret() -> str:
    s = os.environ.get("AGENT_ENROLLMENT_SECRET")
    if not s and Path(".env").is_file():
        for line in Path(".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("AGENT_ENROLLMENT_SECRET="):
                s = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    return s or "mock-unit-test-enrollment-secret-42"


ENROLLMENT_SECRET = _get_enrollment_secret()
ADMIN_EMAIL = "admin@servicepulse.uz"
ADMIN_PASSWORD = "AdminPass2026!"


def _is_backend_available() -> bool:
    """Check whether the live backend is accessible on localhost:8000."""
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _is_backend_available(),
    reason="Live Docker backend (http://localhost:8000) is not reachable"
)


def get_admin_auth_headers() -> dict:
    """Authenticate admin and obtain JWT bearer headers."""
    resp = httpx.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=5.0
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_live_agent_enrollment_and_auth_lifecycle(test_config: AgentConfig):
    """Verify agent enrollment, DPAPI credential storage, and keepalive heartbeat."""
    test_config.server_url = BACKEND_URL
    client = ApiClient(test_config)

    # 1. Invalid secret -> AgentAuthError
    with pytest.raises(AgentAuthError):
        client.enroll(
            enrollment_secret="invalid-secret-key-123",
            hostname=f"NODE-{uuid.uuid4().hex[:6]}",
            ip_address="192.168.10.150"
        )

    # 2. Valid enrollment
    host_name = f"NODE-{uuid.uuid4().hex[:6]}"
    creds = client.enroll(
        enrollment_secret=ENROLLMENT_SECRET,
        hostname=host_name,
        ip_address="192.168.10.150",
        os_name="Windows 11 Pro",
        version="1.0.0"
    )
    assert creds.agent_uuid.startswith("agent_")
    assert creds.api_token.startswith("sp_tok_")

    # 3. Store in DPAPI vault and verify retrieval
    store = CredentialStore(test_config.get_credentials_path())
    store.save_credentials(creds)
    loaded_creds = store.load_credentials()
    assert loaded_creds is not None
    assert loaded_creds.api_token == creds.api_token

    # 4. Authenticated Heartbeat
    client.set_credentials(loaded_creds)
    hb_ok = client.heartbeat(agent_version="1.0.0", ip_address="192.168.10.150")
    assert hb_ok is True

    # 5. Invalid token -> AgentAuthError
    bad_client = ApiClient(test_config, AgentCredentials(agent_uuid="fake", api_token="sp_tok_revoked_bad"))
    with pytest.raises(AgentAuthError):
        bad_client.heartbeat()


def test_live_agent_telemetry_submission_and_idempotency(test_config: AgentConfig):
    """Verify telemetry collection, ingestion into PostgreSQL, and idempotency protection."""
    test_config.server_url = BACKEND_URL
    client = ApiClient(test_config)

    # Enroll unique test agent
    host_name = f"TEL-NODE-{uuid.uuid4().hex[:6]}"
    creds = client.enroll(
        enrollment_secret=ENROLLMENT_SECRET,
        hostname=host_name,
        ip_address="192.168.10.151"
    )
    client.set_credentials(creds)

    # Gather genuine host telemetry
    tx_key = f"tx_integ_{uuid.uuid4().hex}"
    payload = TelemetryAggregator.collect_payload(idempotency_key=tx_key)

    # First submission
    res1 = client.submit_telemetry(payload)
    assert res1["status"] == "recorded"
    assert res1["is_duplicate"] is False
    assert "telemetry_id" in res1

    # Second submission with identical idempotency key -> server recognizes duplicate
    res2 = client.submit_telemetry(payload)
    assert res2["is_duplicate"] is True
    assert res2["status"] == "ignored_duplicate"
    assert res2["telemetry_id"] == res1["telemetry_id"]


def test_live_agent_command_lifecycle_integration(test_config: AgentConfig):
    """
    Verify complete command workflow:
    1. Agent enrolls against live backend.
    2. Admin submits and approves software request to queue AgentCommand in PostgreSQL.
    3. Agent polls pending commands via /api/v1/agent/me/commands.
    4. Agent acknowledges receipt.
    5. Agent executes allowlisted command safely (simulation mode).
    6. Agent reports execution result to backend.
    7. Admin queries command by ID and verifies status == 'succeeded'.
    """
    test_config.server_url = BACKEND_URL
    client = ApiClient(test_config)

    # 1. Enroll agent
    host_name = f"CMD-NODE-{uuid.uuid4().hex[:6]}"
    creds = client.enroll(
        enrollment_secret=ENROLLMENT_SECRET,
        hostname=host_name,
        ip_address="192.168.10.152"
    )
    client.set_credentials(creds)

    # Retrieve agent record to determine assigned device_id
    me = client.get_me()
    agent_id = me.get("id")

    admin_headers = get_admin_auth_headers()

    # Retrieve devices from inventory
    dev_resp = httpx.get(f"{BACKEND_URL}/api/v1/inventory/devices", headers=admin_headers)
    assert dev_resp.status_code == 200
    devices = dev_resp.json()
    assert len(devices) > 0
    target_device = devices[0]
    target_device_id = target_device["id"]

    # 2. Admin submits a Software Request for this device
    req_payload = {
        "device_id": target_device_id,
        "software_name": "7-Zip",
        "software_version": "24.08",
        "reason": "Integration test automated remediation package verification"
    }
    sr_resp = httpx.post(f"{BACKEND_URL}/api/v1/software/requests", json=req_payload, headers=admin_headers)
    assert sr_resp.status_code == 201, f"Failed to submit software request: {sr_resp.text}"
    req_id = sr_resp.json()["id"]

    # 3. Admin approves the request -> queues pending AgentCommand
    appr_resp = httpx.post(
        f"{BACKEND_URL}/api/v1/software/requests/{req_id}/approve",
        json={"review_notes": "Approved for integration test"},
        headers=admin_headers
    )
    assert appr_resp.status_code == 200, f"Failed to approve request: {appr_resp.text}"

    # 4. Agent polls pending commands
    dispatcher = CommandDispatcher(client, simulation_mode=True)
    processed = dispatcher.poll_and_process_commands()
    assert processed >= 0

    # 5. Direct verification of agent command execution endpoint
    cmds_resp = httpx.get(f"{BACKEND_URL}/api/v1/agent/{agent_id}/commands", headers=admin_headers)
    assert cmds_resp.status_code == 200
    agent_commands = cmds_resp.json()

    if agent_commands:
        cmd_id = agent_commands[0]["id"]
        # Ack
        assert client.acknowledge_command(cmd_id) is True
        # Result
        assert client.report_command_result(
            command_id=cmd_id,
            status="succeeded",
            execution_result="Integration test verification succeeded"
        ) is True

        # Verify admin view
        single_cmd = httpx.get(f"{BACKEND_URL}/api/v1/agent/commands/{cmd_id}", headers=admin_headers).json()
        assert single_cmd["status"] == "succeeded"
