"""
ServicePulse - Agent Management & Telemetry Ingestion Service
Handles secure enrollment, per-agent token authentication, heartbeats, and idempotent telemetry.
Author: Muhammadyusuf Usmonov
"""
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.core.dependencies import hash_agent_token
from backend.app.models.agent import Agent, AgentCommand, AgentTelemetry
from backend.app.models.audit import AuditLog
from backend.app.models.inventory import Device
from backend.app.models.organization import Organization
from backend.app.models.user import User
from backend.app.schemas.agent import (
    AgentBootstrapConfigResponse,
    AgentCommandResultRequest,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentTelemetryRequest,
    AgentTelemetryResponse,
)
from backend.app.services.ws_manager import ws_manager


class AgentService:
    @staticmethod
    async def enroll_agent(enroll_in: AgentEnrollRequest, db: AsyncSession) -> AgentEnrollResponse:
        """Secure agent enrollment using global pre-shared enrollment secret."""
        # Enforce constant-time comparison against environment enrollment secret
        if not settings.AGENT_ENROLLMENT_SECRET or not secrets.compare_digest(
            enroll_in.enrollment_secret, settings.AGENT_ENROLLMENT_SECRET
        ):
            # Audit unauthorized enrollment attempt
            db.add(AuditLog(
                user_id=None,
                action="agent_enroll_unauthorized",
                target_resource="agent",
                target_id=enroll_in.hostname,
                status="failure",
                details=f"Invalid enrollment secret attempted from {enroll_in.ip_address}",
            ))
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent enrollment secret",
            )

        agent_uuid = f"agent_{uuid.uuid4().hex[:16]}"
        raw_token = f"sp_tok_{secrets.token_urlsafe(32)}"
        token_hash = hash_agent_token(raw_token)

        # Validate or associate device
        device_id = enroll_in.device_id
        dev = None
        if device_id:
            dev = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
            if not dev:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified device not found")
        else:
            # Look up device by hostname or create a new workstation record
            q_dev = select(Device).where(Device.hostname == enroll_in.hostname.strip())
            dev = (await db.execute(q_dev)).scalar_one_or_none()
            if dev:
                device_id = dev.id

        org_id = enroll_in.organization_id
        if dev and dev.organization_id:
            org_id = dev.organization_id

        agent = Agent(
            device_id=device_id,
            organization_id=org_id,
            agent_uuid=agent_uuid,
            api_token_hash=token_hash,
            status="active",
            version=enroll_in.version,
            hostname=enroll_in.hostname.strip(),
            ip_address=enroll_in.ip_address.strip(),
            os_name=enroll_in.os_name,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(agent)
        await db.flush()

        db.add(AuditLog(
            user_id=None,
            organization_id=org_id,
            action="agent_enrolled",
            target_resource="agent",
            target_id=str(agent.id),
            status="success",
            details=f"Agent enrolled for host {agent.hostname} ({agent.agent_uuid})",
        ))
        await db.commit()

        return AgentEnrollResponse(
            agent_uuid=agent.agent_uuid,
            api_token=raw_token,
            device_id=agent.device_id,
            organization_id=agent.organization_id,
            status="active",
            message="Agent successfully enrolled. Keep api_token secure on the host.",
        )

    @staticmethod
    async def record_heartbeat(
        agent: Agent,
        hb_in: AgentHeartbeatRequest,
        db: AsyncSession
    ) -> AgentHeartbeatResponse:
        """Record periodic keepalive heartbeat from agent."""
        now = datetime.now(timezone.utc)
        agent.last_seen = now
        if hb_in.agent_version:
            agent.version = hb_in.agent_version
        if hb_in.ip_address:
            agent.ip_address = hb_in.ip_address

        if agent.device_id:
            dev = (await db.execute(select(Device).where(Device.id == agent.device_id))).scalar_one_or_none()
            if dev:
                dev.last_heartbeat = now
                dev.last_seen = now
                dev.status = "online"
                dev.consecutive_failures = 0
                db.add(dev)

        db.add(agent)
        await db.commit()

        return AgentHeartbeatResponse(
            status="acknowledged",
            server_time=now,
            acknowledged=True,
        )

    @staticmethod
    async def record_telemetry(
        agent: Agent,
        tel_in: AgentTelemetryRequest,
        db: AsyncSession
    ) -> AgentTelemetryResponse:
        """Idempotent ingestion of agent system telemetry metrics."""
        # 1. Idempotency Check
        if tel_in.idempotency_key:
            q_existing = select(AgentTelemetry).where(
                AgentTelemetry.idempotency_key == tel_in.idempotency_key.strip()
            )
            existing = (await db.execute(q_existing)).scalar_one_or_none()
            if existing:
                return AgentTelemetryResponse(
                    status="ignored_duplicate",
                    telemetry_id=existing.id,
                    is_duplicate=True,
                    message="Telemetry record with this idempotency key already exists",
                )

        now = datetime.now(timezone.utc)
        record_time = tel_in.recorded_at or now

        telemetry = AgentTelemetry(
            agent_id=agent.id,
            cpu_percent=tel_in.cpu_percent,
            ram_percent=tel_in.ram_percent,
            ram_used_mb=tel_in.ram_used_mb,
            ram_total_mb=tel_in.ram_total_mb,
            disk_percent=tel_in.disk_percent,
            disk_used_gb=tel_in.disk_used_gb,
            disk_total_gb=tel_in.disk_total_gb,
            windows_activation_status=tel_in.windows_activation_status,
            windows_defender_status=tel_in.windows_defender_status,
            recorded_at=record_time,
            idempotency_key=tel_in.idempotency_key.strip() if tel_in.idempotency_key else None,
        )
        db.add(telemetry)

        # Update agent and device last seen
        agent.last_seen = now
        db.add(agent)

        if agent.device_id:
            dev = (await db.execute(select(Device).where(Device.id == agent.device_id))).scalar_one_or_none()
            if dev:
                dev.last_seen = now
                dev.status = "online"
                dev.consecutive_failures = 0
                db.add(dev)

        await db.commit()
        await db.refresh(telemetry)

        if agent.organization_id:
            await ws_manager.broadcast_to_org(
                agent.organization_id,
                "device:telemetry",
                {
                    "agent_id": agent.id,
                    "device_id": agent.device_id,
                    "hostname": agent.hostname,
                    "cpu_percent": tel_in.cpu_percent,
                    "ram_percent": tel_in.ram_percent,
                    "disk_percent": tel_in.disk_percent,
                    "windows_activation_status": tel_in.windows_activation_status,
                    "windows_defender_status": tel_in.windows_defender_status,
                    "recorded_at": record_time.isoformat(),
                },
            )

        return AgentTelemetryResponse(
            status="recorded",
            telemetry_id=telemetry.id,
            is_duplicate=False,
            message="Telemetry successfully recorded",
        )

    @staticmethod
    async def list_agents(
        skip: int,
        limit: int,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> List[Agent]:
        q = select(Agent).order_by(Agent.id).offset(skip).limit(limit)
        if scoped_org_id is not None:
            q = q.where(Agent.organization_id == scoped_org_id)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_agent_by_id(
        agent_id: int,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Agent:
        q = select(Agent).where(Agent.id == agent_id)
        agent = (await db.execute(q)).scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        if scoped_org_id is not None and agent.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    @staticmethod
    async def get_agent_telemetry(
        agent_id: int,
        skip: int,
        limit: int,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> List[AgentTelemetry]:
        agent = await AgentService.get_agent_by_id(agent_id, db, scoped_org_id=scoped_org_id)
        q = (
            select(AgentTelemetry)
            .where(AgentTelemetry.agent_id == agent.id)
            .order_by(AgentTelemetry.recorded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_agent_commands(
        agent_id: int,
        skip: int,
        limit: int,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> List[AgentCommand]:
        agent = await AgentService.get_agent_by_id(agent_id, db, scoped_org_id=scoped_org_id)
        q = (
            select(AgentCommand)
            .where(AgentCommand.agent_id == agent.id)
            .order_by(AgentCommand.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_command_by_id(
        command_id: int,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> AgentCommand:
        q = select(AgentCommand).options(selectinload(AgentCommand.agent)).where(AgentCommand.id == command_id)
        cmd = (await db.execute(q)).scalar_one_or_none()
        if not cmd:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
        if scoped_org_id is not None and cmd.agent and cmd.agent.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
        return cmd

    @staticmethod
    async def get_agent_pending_commands(
        agent: Agent,
        db: AsyncSession,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentCommand]:
        """Fetch pending/dispatched commands assigned to the calling agent."""
        q = select(AgentCommand).where(AgentCommand.agent_id == agent.id)
        if status_filter:
            q = q.where(AgentCommand.status == status_filter)
        else:
            q = q.where(AgentCommand.status.in_(["pending", "dispatched", "acknowledged"]))
        q = q.order_by(AgentCommand.created_at.asc()).limit(limit)
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def acknowledge_agent_command(
        agent: Agent,
        command_id: int,
        db: AsyncSession,
    ) -> AgentCommand:
        """Acknowledge receipt of a command by the assigned agent."""
        q = select(AgentCommand).where(AgentCommand.id == command_id)
        cmd = (await db.execute(q)).scalar_one_or_none()
        if not cmd or cmd.agent_id != agent.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found for this agent")

        cmd.status = "acknowledged"
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
        return cmd

    @staticmethod
    async def report_agent_command_result(
        agent: Agent,
        command_id: int,
        result_in: AgentCommandResultRequest,
        db: AsyncSession,
    ) -> AgentCommand:
        """Record command execution result submitted by the assigned agent."""
        q = select(AgentCommand).where(AgentCommand.id == command_id)
        cmd = (await db.execute(q)).scalar_one_or_none()
        if not cmd or cmd.agent_id != agent.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found for this agent")

        from backend.app.core.security import redact_sensitive_text

        now = datetime.now(timezone.utc)
        sanitized_result = redact_sensitive_text(result_in.execution_result)
        cmd.status = result_in.status
        cmd.execution_result = sanitized_result
        cmd.executed_at = result_in.executed_at or now
        db.add(cmd)

        # If linked to a RemediationExecution, update execution and trigger verification
        if cmd.remediation_execution_id:
            from backend.app.models.remediation import RemediationExecution
            from backend.app.services.remediation_verification import RemediationVerification

            q_ex = select(RemediationExecution).where(RemediationExecution.id == cmd.remediation_execution_id)
            ex = (await db.execute(q_ex)).scalar_one_or_none()
            if ex:
                ex.status = result_in.status
                if sanitized_result:
                    ex.execution_log = f"{ex.execution_log or ''}\nAgent Result: {sanitized_result}".strip()
                db.add(ex)
                await db.flush()
                if result_in.status == "succeeded":
                    await RemediationVerification.verify_execution(ex.id, db)

        db.add(AuditLog(
            user_id=cmd.requested_by_user_id,
            organization_id=agent.organization_id,
            action="agent_command_executed",
            target_resource="agent_command",
            target_id=str(cmd.id),
            status=result_in.status,
            details=f"Agent {agent.agent_uuid} executed {cmd.action_name} with result {result_in.status}",
        ))
        await db.commit()
        await db.refresh(cmd)
        return cmd

    # -------------------------------------------------------------------------
    # Stage 6: 1-Click Agent Bootstrap Deployer
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_bootstrap_config(
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> AgentBootstrapConfigResponse:
        target_org_id = scoped_org_id or actor.organization_id or 1
        q_org = select(Organization).where(Organization.id == target_org_id)
        org = (await db.execute(q_org)).scalar_one_or_none()
        org_name = org.name if org else "ServicePulse Organization"

        server_url = "http://localhost:8000"
        secret = settings.AGENT_ENROLLMENT_SECRET or "sp-enrollment-secret-2026"
        if len(secret) > 8:
            masked_secret = f"{secret[:4]}***{secret[-4:]}"
        else:
            masked_secret = "****"

        powershell_cmd = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; "
            f"iex ((New-Object System.Net.WebClient).DownloadString('{server_url}/static/Install-ServicePulseAgent.ps1')); "
            f"Install-ServicePulseAgent -ServerUrl '{server_url}' -EnrollmentSecret '{secret}' -OrgId {target_org_id}"
        )

        linux_cmd = (
            f"curl -fsSL {server_url}/static/install_agent.sh | "
            f"sudo bash -s -- --server-url {server_url} --enrollment-secret {secret} --org-id {target_org_id}"
        )

        manual_steps = [
            "Open an elevated administrative console (PowerShell 5.1+ as Administrator on Windows, or sudo on Linux).",
            "Execute the 1-click bootstrap command above to register the host into ServicePulse CMDB.",
            "The agent will automatically establish mutual HMAC TLS handshake and begin real-time telemetry streaming."
        ]

        return AgentBootstrapConfigResponse(
            server_url=server_url,
            organization_id=target_org_id,
            organization_name=org_name,
            enrollment_secret_masked=masked_secret,
            powershell_command=powershell_cmd,
            linux_bash_command=linux_cmd,
            manual_steps=manual_steps,
            agent_version="1.0.0",
        )

