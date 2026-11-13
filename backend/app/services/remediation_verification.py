"""
ServicePulse - Automated Remediation Verification Engine
Verifies execution outcomes against observable evidence.
Ensures simulated executions are never counted as real success, and offline devices
without an agent are reported as pending or unavailable rather than falsely verified.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.agent import Agent, AgentCommand
from backend.app.models.inventory import Device
from backend.app.models.remediation import RemediationExecution
from backend.app.workers.probe_engine import ProbeEngine


class RemediationVerification:
    """
    Independent verification of remediation actions.
    Checks observable evidence before marking an execution verified.
    """

    @staticmethod
    async def verify_execution(
        execution_id: int,
        db: AsyncSession
    ) -> Tuple[bool, str]:
        """
        Evaluate observable evidence for a remediation execution:
        1. If simulated: mark verified_status = 'simulated_success', explicitly NOT real success.
        2. If device is offline and has no active agent: cannot verify success -> 'unavailable'.
        3. If action is recheck_network_endpoint: perform follow-up probe and check if reachable.
        4. If command has agent execution result: verify agent reported status 'succeeded'.
        """
        q = (
            select(RemediationExecution)
            .options(
                selectinload(RemediationExecution.device),
                selectinload(RemediationExecution.incident),
                selectinload(RemediationExecution.agent_command),
                selectinload(RemediationExecution.rule),
            )
            .where(RemediationExecution.id == execution_id)
        )
        execution = (await db.execute(q)).scalar_one_or_none()
        if not execution:
            return False, "Remediation execution not found"

        now = datetime.now(timezone.utc)
        execution.verified_at = now

        # Case 1: Simulated Execution
        if execution.is_simulation:
            execution.verification_status = "simulated_verification"
            execution.verification_log = "SIMULATED: Action completed in simulation mode. Not counted as production success."
            db.add(execution)
            await db.commit()
            return True, execution.verification_log

        device: Optional[Device] = execution.device
        cmd: Optional[AgentCommand] = execution.agent_command

        # Case 2: Offline device with no agent
        if device and device.status == "offline":
            # Check if device has an agent that is active
            agent_q = select(Agent).where(Agent.device_id == device.id, Agent.status == "active")
            agent = (await db.execute(agent_q)).scalar_one_or_none()
            if not agent:
                execution.verification_status = "unavailable"
                execution.verification_log = "Device is offline with no active agent. Observable evidence unavailable."
                db.add(execution)
                await db.commit()
                return False, execution.verification_log

        # Case 3: Action is recheck_network_endpoint
        if execution.rule and execution.rule.action_name == "recheck_network_endpoint" and device:
            probe_res = await ProbeEngine.probe_device(
                device_id=device.id,
                ip_address=device.ip_address,
                check_type="icmp_ping",
                timeout_seconds=2.0,
                use_simulation=device.is_sample_data,
            )
            if probe_res.is_successful:
                execution.verification_status = "verified_success"
                execution.verification_log = f"Verified: Device responded to follow-up probe ({probe_res.response_time_ms}ms)."
                execution.status = "success"
                db.add(execution)
                await db.commit()
                return True, execution.verification_log
            else:
                execution.verification_status = "verification_failed"
                execution.verification_log = "Follow-up probe failed: Device still unreachable."
                db.add(execution)
                await db.commit()
                return False, execution.verification_log

        # Case 4: AgentCommand status verification
        if cmd:
            if cmd.status == "succeeded":
                execution.verification_status = "verified_success"
                execution.status = "success"
                execution.verification_log = f"Agent confirmed successful execution: {cmd.execution_result or 'OK'}"
                db.add(execution)
                await db.commit()
                return True, execution.verification_log
            elif cmd.status in ("failed", "rejected", "cancelled", "expired"):
                execution.verification_status = "verification_failed"
                execution.status = "failure"
                execution.verification_log = f"Agent command reported failure: {cmd.execution_result or cmd.status}"
                db.add(execution)
                await db.commit()
                return False, execution.verification_log
            else:
                execution.verification_status = "pending"
                execution.verification_log = f"Awaiting agent command execution (current status: {cmd.status})"
                db.add(execution)
                await db.commit()
                return False, execution.verification_log

        # Default fallback
        execution.verification_status = "pending"
        execution.verification_log = "Pending observable evidence."
        db.add(execution)
        await db.commit()
        return False, execution.verification_log
