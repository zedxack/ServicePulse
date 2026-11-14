"""
ServicePulse - Agent Enrollment, Heartbeat & Telemetry API Integration Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient

from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_agent_enrollment_security(client: AsyncClient):
    """Verify agent enrollment requires valid enrollment secret."""
    # Invalid secret -> 401
    bad_resp = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": "wrong-secret-key",
            "hostname": "TEST-HOST-01",
            "ip_address": "192.168.10.150"
        }
    )
    assert bad_resp.status_code == 401

    # Valid secret -> 201 Created
    good_resp = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": settings.AGENT_ENROLLMENT_SECRET,
            "hostname": "TEST-HOST-01",
            "ip_address": "192.168.10.150",
            "os_name": "Windows 11 Enterprise",
            "version": "1.0.0"
        }
    )
    assert good_resp.status_code == 201
    data = good_resp.json()
    assert "agent_uuid" in data
    assert "api_token" in data
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_agent_heartbeat_and_telemetry_flow(client: AsyncClient):
    """Verify agent heartbeat, telemetry ingestion, and idempotency protection."""
    # 1. Enroll agent
    enroll_resp = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": settings.AGENT_ENROLLMENT_SECRET,
            "hostname": "LAB2-PC01",
            "ip_address": "192.168.10.21",
            "os_name": "Windows 11 Pro",
            "version": "1.0.0"
        }
    )
    agent_data = enroll_resp.json()
    api_token = agent_data["api_token"]
    agent_headers = {"X-Agent-Token": api_token}

    # 2. Check /agent/me
    me_resp = await client.get("/api/v1/agent/me", headers=agent_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["agent_uuid"] == agent_data["agent_uuid"]

    # 3. Heartbeat
    hb_resp = await client.post("/api/v1/agent/heartbeat", json={"agent_version": "1.0.1"}, headers=agent_headers)
    assert hb_resp.status_code == 200
    assert hb_resp.json()["acknowledged"] is True

    # 4. Telemetry Ingestion
    telemetry_payload = {
        "cpu_percent": 34.5,
        "ram_percent": 62.0,
        "ram_used_mb": 9920.0,
        "ram_total_mb": 16000.0,
        "disk_percent": 45.2,
        "disk_used_gb": 180.5,
        "disk_total_gb": 400.0,
        "windows_activation_status": "Licensed",
        "windows_defender_status": "Active",
        "idempotency_key": "idemp-key-tx-001"
    }
    tel_resp = await client.post("/api/v1/agent/telemetry", json=telemetry_payload, headers=agent_headers)
    assert tel_resp.status_code == 201
    assert tel_resp.json()["status"] == "recorded"
    assert tel_resp.json()["is_duplicate"] is False

    # 5. Idempotent Resubmission with same key -> should NOT fail, returns duplicate notice
    dup_resp = await client.post("/api/v1/agent/telemetry", json=telemetry_payload, headers=agent_headers)
    assert dup_resp.status_code == 201
    assert dup_resp.json()["is_duplicate"] is True
    assert dup_resp.json()["status"] == "ignored_duplicate"


@pytest.mark.asyncio
async def test_agent_command_lifecycle(client: AsyncClient, test_db):
    """Verify agent command polling, acknowledgment, and result reporting."""
    from backend.app.models.agent import Agent, AgentCommand

    # 1. Enroll agent
    enroll_resp = await client.post(
        "/api/v1/agent/enroll",
        json={
            "enrollment_secret": settings.AGENT_ENROLLMENT_SECRET,
            "hostname": "CMD-HOST-01",
            "ip_address": "192.168.10.22",
            "os_name": "Windows 11 Pro",
            "version": "1.0.0"
        }
    )
    agent_data = enroll_resp.json()
    api_token = agent_data["api_token"]
    agent_headers = {"X-Agent-Token": api_token}

    # Query agent DB record to get id
    from sqlalchemy import select
    res = await test_db.execute(select(Agent).where(Agent.agent_uuid == agent_data["agent_uuid"]))
    agent = res.scalar_one()

    # 2. Insert a pending AgentCommand for this agent
    cmd = AgentCommand(
        agent_id=agent.id,
        device_id=agent.device_id,
        action_name="restart_service",
        parameters='{"service_name": "spooler"}',
        status="pending",
        verification_status="pending",
    )
    test_db.add(cmd)
    await test_db.commit()
    await test_db.refresh(cmd)

    # 3. Agent polls pending commands via /api/v1/agent/me/commands
    poll_resp = await client.get("/api/v1/agent/me/commands?status=pending", headers=agent_headers)
    assert poll_resp.status_code == 200
    cmds = poll_resp.json()
    assert len(cmds) == 1
    assert cmds[0]["id"] == cmd.id
    assert cmds[0]["action_name"] == "restart_service"

    # Also check /api/v1/agent/commands/pending alias
    alias_resp = await client.get("/api/v1/agent/commands/pending", headers=agent_headers)
    assert alias_resp.status_code == 200
    assert len(alias_resp.json()) == 1

    # 4. Agent acknowledges command receipt
    ack_resp = await client.post(f"/api/v1/agent/me/commands/{cmd.id}/ack", headers=agent_headers)
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    # 5. Agent submits execution result
    result_payload = {
        "status": "succeeded",
        "execution_result": "Service 'spooler' restarted successfully. Service status: RUNNING."
    }
    res_resp = await client.post(f"/api/v1/agent/me/commands/{cmd.id}/result", json=result_payload, headers=agent_headers)
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "succeeded"

    # 6. Verify DB state of command
    await test_db.refresh(cmd)
    assert cmd.status == "succeeded"
    assert "Service 'spooler' restarted successfully" in cmd.execution_result
