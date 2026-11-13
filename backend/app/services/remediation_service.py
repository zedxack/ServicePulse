"""
ServicePulse - Automated Remediation Service
Coordinates incident response, rule matching, policy evaluation, approval workflows,
safe command creation, and execution tracking.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.agent import Agent, AgentCommand
from backend.app.models.incident import Incident, IncidentEvent
from backend.app.models.inventory import Device
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.models.user import User
from backend.app.services.remediation_policy import RemediationPolicy


class RemediationService:
    """
    Core service managing automated remediation lifecycle from incident detection to verification.
    """

    @staticmethod
    async def evaluate_incident_remediation(
        incident_id: int,
        db: AsyncSession
    ) -> List[RemediationExecution]:
        """
        Evaluate active remediation rules for an active incident:
        1. Find matching rules for incident's organization and trigger condition.
        2. Verify policy, allowlist, cooldown, and retries.
        3. If approval required -> create pending_approval execution.
        4. If approved/auto -> create executing execution and queue AgentCommand.
        """
        if not settings.ENABLE_AUTOMATED_REMEDIATION:
            return []

        inc_q = (
            select(Incident)
            .options(selectinload(Incident.device))
            .where(Incident.id == incident_id)
        )
        incident = (await db.execute(inc_q)).scalar_one_or_none()
        if not incident or incident.status == "resolved":
            return []

        device = incident.device
        org_id = incident.organization_id

        # Determine trigger condition based on incident severity / title
        trigger = "device_offline" if "unreachable" in incident.title.lower() else "service_down"

        # Query active rules for this tenant (or platform global rules)
        rules_q = select(RemediationRule).where(
            RemediationRule.is_active.is_(True),
            RemediationRule.trigger_condition.in_([trigger, "all_failures", "agent_offline"]),
        )
        if org_id is not None:
            rules_q = rules_q.where(
                (RemediationRule.organization_id == org_id) | (RemediationRule.organization_id.is_(None))
            )
        rules = list((await db.execute(rules_q)).scalars().all())

        executions: List[RemediationExecution] = []
        now = datetime.now(timezone.utc)

        for rule in rules:
            # 1. Action allowlist validation
            is_valid, err, val_params = RemediationPolicy.validate_action(rule.action_name, rule.action_parameters)
            if not is_valid:
                logger.warning("Remediation rule %s failed action allowlist: %s", rule.name, err)
                continue

            # 2. Eligibility & Cooldown check
            eligible, reason = await RemediationPolicy.check_execution_eligibility(rule, device, db)
            if not eligible:
                logger.info("Rule %s skipped for incident %s: %s", rule.name, incident.id, reason)
                continue

            # Determine if execution is in simulation mode
            is_sim = False
            if device and (device.is_sample_data or settings.WORKER_SIMULATION_MODE):
                is_sim = True

            # 3. Handle approval requirement
            if rule.requires_approval:
                exc = RemediationExecution(
                    rule_id=rule.id,
                    incident_id=incident.id,
                    device_id=device.id if device else None,
                    status="pending_approval",
                    verification_status="pending",
                    is_simulation=is_sim,
                    execution_log=f"Action '{rule.action_name}' queued. Awaiting administrator approval.",
                )
                db.add(exc)
                await db.flush()

                db.add(IncidentEvent(
                    incident_id=incident.id,
                    event_type="remediation_pending_approval",
                    message=f"Remediation rule '{rule.name}' matched. Requires administrator approval before execution.",
                    created_at=now,
                ))
                executions.append(exc)
            else:
                # 4. Immediate execution dispatch
                exc = await RemediationService._dispatch_execution(rule, incident, device, is_sim, db, actor=None)
                if exc:
                    executions.append(exc)

        await db.commit()
        return executions

    @staticmethod
    async def _dispatch_execution(
        rule: RemediationRule,
        incident: Incident,
        device: Optional[Device],
        is_simulation: bool,
        db: AsyncSession,
        actor: Optional[User] = None
    ) -> RemediationExecution:
        """Create execution record, queue AgentCommand, and update incident events."""
        now = datetime.now(timezone.utc)

        exc = RemediationExecution(
            rule_id=rule.id,
            incident_id=incident.id,
            device_id=device.id if device else None,
            status="executing",
            verification_status="pending",
            is_simulation=is_simulation,
            approved_by_user_id=actor.id if actor else None,
            execution_log=f"Dispatched allowlisted action '{rule.action_name}' by {'automation' if not actor else actor.email}",
        )
        db.add(exc)
        await db.flush()

        # Check if device has an agent to receive the command
        agent = None
        if device:
            agent_q = select(Agent).where(Agent.device_id == device.id)
            agent = (await db.execute(agent_q)).scalar_one_or_none()

        if agent:
            # Create AgentCommand
            cmd = AgentCommand(
                agent_id=agent.id,
                device_id=device.id,
                action_name=rule.action_name,
                parameters=rule.action_parameters,
                status="pending",
                verification_status="pending",
                is_simulation=is_simulation,
                remediation_execution_id=exc.id,
                requested_by_user_id=actor.id if actor else None,
            )
            db.add(cmd)
            await db.flush()
            exc.agent_command_id = cmd.id

        event_msg = (
            f"Remediation dispatched: rule '{rule.name}', action '{rule.action_name}' "
            f"({'Simulation Mode' if is_simulation else 'Live'})."
        )
        db.add(IncidentEvent(
            incident_id=incident.id,
            event_type="remediation_dispatched",
            message=event_msg,
            created_by_user_id=actor.id if actor else None,
            created_at=now,
        ))
        return exc

    @staticmethod
    async def approve_execution(
        execution_id: int,
        approver: User,
        review_notes: Optional[str],
        db: AsyncSession
    ) -> RemediationExecution:
        """Approve a pending remediation execution and dispatch the action."""
        q = (
            select(RemediationExecution)
            .options(
                selectinload(RemediationExecution.rule),
                selectinload(RemediationExecution.incident),
                selectinload(RemediationExecution.device)
            )
            .where(RemediationExecution.id == execution_id)
        )
        exc = (await db.execute(q)).scalar_one_or_none()
        if not exc:
            raise ValueError("Remediation execution not found")
        if exc.status != "pending_approval":
            raise ValueError(f"Execution status '{exc.status}' cannot be approved")

        now = datetime.now(timezone.utc)
        exc.status = "approved"
        exc.approved_by_user_id = approver.id
        exc.execution_log = f"Approved by {approver.email}: {review_notes or 'No notes'}"

        # Dispatch command
        is_sim = exc.is_simulation
        if exc.device and (exc.device.is_sample_data or settings.WORKER_SIMULATION_MODE):
            is_sim = True

        agent = None
        if exc.device:
            agent_q = select(Agent).where(Agent.device_id == exc.device.id)
            agent = (await db.execute(agent_q)).scalar_one_or_none()

        if agent:
            cmd = AgentCommand(
                agent_id=agent.id,
                device_id=exc.device.id,
                action_name=exc.rule.action_name,
                parameters=exc.rule.action_parameters,
                status="pending",
                verification_status="pending",
                is_simulation=is_sim,
                remediation_execution_id=exc.id,
                requested_by_user_id=approver.id,
            )
            db.add(cmd)
            await db.flush()
            exc.agent_command_id = cmd.id

        exc.status = "executing"
        if exc.incident:
            db.add(IncidentEvent(
                incident_id=exc.incident_id,
                event_type="remediation_approved",
                message=f"Remediation '{exc.rule.name}' approved by {approver.full_name} ({approver.email}).",
                created_by_user_id=approver.id,
                created_at=now,
            ))

        await db.commit()
        await db.refresh(exc)
        return exc

    @staticmethod
    async def reject_execution(
        execution_id: int,
        reviewer: User,
        review_notes: Optional[str],
        db: AsyncSession
    ) -> RemediationExecution:
        """Reject a pending remediation execution."""
        q = (
            select(RemediationExecution)
            .options(selectinload(RemediationExecution.rule))
            .where(RemediationExecution.id == execution_id)
        )
        exc = (await db.execute(q)).scalar_one_or_none()
        if not exc:
            raise ValueError("Remediation execution not found")
        if exc.status != "pending_approval":
            raise ValueError(f"Execution status '{exc.status}' cannot be rejected")

        now = datetime.now(timezone.utc)
        exc.status = "rejected"
        exc.approved_by_user_id = reviewer.id
        exc.execution_log = f"Rejected by {reviewer.email}: {review_notes or 'No reason provided'}"
        exc.verification_status = "rejected"

        if exc.incident_id:
            db.add(IncidentEvent(
                incident_id=exc.incident_id,
                event_type="remediation_rejected",
                message=f"Remediation '{exc.rule.name}' rejected by {reviewer.full_name} ({reviewer.email}).",
                created_by_user_id=reviewer.id,
                created_at=now,
            ))

        await db.commit()
        await db.refresh(exc)
        return exc
