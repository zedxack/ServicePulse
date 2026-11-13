"""
ServicePulse - Agent Enrollment, Heartbeat & Telemetry Endpoints
Author: Muhammadyusuf Usmonov
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_agent
from backend.app.db.session import get_db
from backend.app.models.agent import Agent
from backend.app.schemas.agent import (
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRead,
    AgentTelemetryRequest,
    AgentTelemetryResponse,
)
from backend.app.services.agent_service import AgentService

router = APIRouter()


@router.post(
    "/enroll",
    response_model=AgentEnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll and authenticate a new remote monitoring agent"
)
async def enroll_agent(
    req: AgentEnrollRequest,
    db: AsyncSession = Depends(get_db)
) -> AgentEnrollResponse:
    return await AgentService.enroll_agent(req, db)


@router.post(
    "/heartbeat",
    response_model=AgentHeartbeatResponse,
    summary="Agent keepalive heartbeat probe"
)
async def record_heartbeat(
    req: AgentHeartbeatRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentHeartbeatResponse:
    return await AgentService.record_heartbeat(current_agent, req, db)


@router.post(
    "/telemetry",
    response_model=AgentTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Idempotent agent system telemetry submission"
)
async def submit_telemetry(
    req: AgentTelemetryRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentTelemetryResponse:
    return await AgentService.record_telemetry(current_agent, req, db)


@router.get(
    "/me",
    response_model=AgentRead,
    summary="Retrieve current agent registration status"
)
async def get_agent_me(
    current_agent: Agent = Depends(get_current_agent)
) -> Agent:
    return current_agent
