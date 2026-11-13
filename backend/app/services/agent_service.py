"""
ServicePulse - Agent Management & Telemetry Ingestion Service
Handles secure enrollment, per-agent token authentication, heartbeats, and idempotent telemetry.
Author: Muhammadyusuf Usmonov
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.dependencies import hash_agent_token
from backend.app.models.agent import Agent, AgentTelemetry
from backend.app.models.audit import AuditLog
from backend.app.models.inventory import Device
from backend.app.schemas.agent import (
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentTelemetryRequest,
    AgentTelemetryResponse,
)


class AgentService:
    @staticmethod
    async def enroll_agent(enroll_in: AgentEnrollRequest, db: AsyncSession) -> AgentEnrollResponse:
        """Secure agent enrollment using global pre-shared enrollment secret."""
        if enroll_in.enrollment_secret != settings.AGENT_ENROLLMENT_SECRET:
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

        return AgentTelemetryResponse(
            status="recorded",
            telemetry_id=telemetry.id,
            is_duplicate=False,
            message="Telemetry successfully recorded",
        )
