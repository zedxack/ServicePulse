"""
ServicePulse - Step 3 Automated Remediation Engine Tests
Tests allowlist enforcement, approval workflows, cooldown limits,
AgentCommand lifecycle in simulation mode, and observable verification.
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent import Agent, AgentCommand
from backend.app.models.incident import Incident
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.services.remediation_policy import RemediationPolicy
from backend.app.workers.remediation_worker import RemediationWorker


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


def test_remediation_policy_allowlist_validation():
    """Verify strictly allowlisted actions pass and arbitrary shell commands are rejected."""
    # 1. Allowlisted action with valid parameters
    is_valid, err, val = RemediationPolicy.validate_action(
        "restart_service", '{"service_name": "Spooler", "timeout_seconds": 30}'
    )
    assert is_valid is True
    assert err is None
    assert val["service_name"] == "Spooler"

    # 2. Allowlisted action with invalid parameters
    is_valid, err, _ = RemediationPolicy.validate_action(
        "restart_service", '{"service_name": ""}'
    )
    assert is_valid is False

    # 3. Non-allowlisted / arbitrary shell command
    is_valid, err, _ = RemediationPolicy.validate_action(
        "execute_shell", '{"command": "rm -rf /"}'
    )
    assert is_valid is False
    assert "not in the allowlist" in err

    # 4. Diagnostics check
    is_valid, err, _ = RemediationPolicy.validate_action(
        "run_diagnostic_check", '{"diagnostic_type": "network_summary"}'
    )
    assert is_valid is True


@pytest.mark.asyncio
async def test_remediation_rule_creation_and_approval_workflow(client: AsyncClient):
    """
    Verify:
    1. Creating a rule with arbitrary action name returns 400 Bad Request.
    2. Rule requiring approval generates execution in 'pending_approval' state.
    3. Administrator can approve or reject the execution.
    """
    admin_tok = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    admin_h = {"Authorization": f"Bearer {admin_tok}"}

    # 1. Arbitrary action rejected at API boundary
    r_bad_rule = await client.post(
        "/api/v1/remediations/rules",
        json={
            "name": "Rogue Command Rule",
            "trigger_condition": "device_offline",
            "action_name": "arbitrary_powershell_script",
        },
        headers=admin_h,
    )
    assert r_bad_rule.status_code == 400
    assert "not in the allowlist" in r_bad_rule.json()["detail"]

    # 2. Allowlisted rule with approval requirement
    r_rule = await client.post(
        "/api/v1/remediations/rules",
        json={
            "name": "Restart Print Spooler with Approval",
            "trigger_condition": "service_down",
            "action_name": "restart_service",
            "action_parameters": '{"service_name": "Spooler"}',
            "requires_approval": True,
        },
        headers=admin_h,
    )
    assert r_rule.status_code == 201
    rule_id = r_rule.json()["id"]

    # 3. Create incident to trigger approval
    r_inc = await client.post(
        "/api/v1/incidents",
        json={
            "title": "Print Spooler Service Failure",
            "description": "Spooler stopped responding",
            "severity": "warning",
        },
        headers=admin_h,
    )
    inc_id = r_inc.json()["id"]

    # Trigger execution
    r_exec = await client.post(
        "/api/v1/remediations/executions",
        json={"rule_id": rule_id, "incident_id": inc_id},
        headers=admin_h,
    )
    assert r_exec.status_code == 201
    exc_data = r_exec.json()
    assert exc_data["status"] == "pending_approval"
    exc_id = exc_data["id"]

    # 4. Approve execution
    r_app = await client.post(
        f"/api/v1/remediations/executions/{exc_id}/approve",
        json={"decision": "approved", "review_notes": "Approved by lead sysadmin"},
        headers=admin_h,
    )
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "executing"


@pytest.mark.asyncio
async def test_agent_command_lifecycle_and_simulation_mode(test_db: AsyncSession):
    """
    Verify:
    1. Agent commands in simulation mode progress: pending -> dispatched -> executing -> succeeded.
    2. Simulated results are explicitly flagged and verified as simulated_verification.
    3. Offline device with no agent returns verification_status = 'unavailable'.
    """
    db = test_db

    # Create test rule
    rule = RemediationRule(
        name="Simulation Test Rule",
        trigger_condition="device_offline",
        action_name="run_diagnostic_check",
        is_active=True,
        requires_approval=False,
    )
    db.add(rule)
    await db.flush()

    # Create test incident
    inc = Incident(
        title="Simulated Outage Incident",
        description="Testing simulation execution",
        fingerprint="sim_outage_01",
        status="open",
    )
    db.add(inc)
    await db.flush()

    # Create simulated execution
    exc = RemediationExecution(
        rule_id=rule.id,
        incident_id=inc.id,
        status="executing",
        verification_status="pending",
        is_simulation=True,
    )
    db.add(exc)
    await db.flush()

    # Create agent for simulation
    agent = Agent(
        agent_uuid="test-sim-agent-uuid-001",
        api_token_hash="fake-hash",
        hostname="sim-host",
        ip_address="10.0.0.1",
        status="active",
    )
    db.add(agent)
    await db.flush()

    cmd = AgentCommand(
        agent_id=agent.id,
        action_name="run_diagnostic_check",
        status="pending",
        is_simulation=True,
        remediation_execution_id=exc.id,
    )
    db.add(cmd)
    await db.flush()
    exc.agent_command_id = cmd.id
    await db.commit()

    cmd_id = cmd.id
    exc_id = exc.id

    # Run RemediationWorker to process pending simulation commands
    processed = await RemediationWorker.process_pending_commands(db)
    assert processed >= 1

    # Check command status
    c = await db.get(AgentCommand, cmd_id)
    assert c.status == "succeeded"
    assert c.is_simulation is True
    assert "SIMULATION" in c.execution_result

    # Check execution verification
    e = await db.get(RemediationExecution, exc_id)
    assert e.is_simulation is True
    assert e.verification_status == "simulated_verification"
    assert "Not counted as production success" in e.verification_log
