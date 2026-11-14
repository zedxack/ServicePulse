"""
ServicePulse - Agent Enrollment, Heartbeat & Telemetry Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_current_agent,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.agent import Agent, AgentCommand
from backend.app.models.user import User
from backend.app.schemas.agent import (
    AgentCommandAckResponse,
    AgentCommandRead,
    AgentCommandResultRequest,
    AgentCommandResultResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRead,
    AgentTelemetryRead,
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


@router.get(
    "/me/commands",
    response_model=List[AgentCommandRead],
    summary="Poll pending remediation commands for the authenticated agent"
)
async def poll_agent_commands(
    status_filter: Optional[str] = Query(None, alias="status", description="Optional filter, e.g. pending"),
    limit: int = Query(50, ge=1, le=100),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> List[AgentCommand]:
    return await AgentService.get_agent_pending_commands(
        current_agent, db, status_filter=status_filter, limit=limit
    )


@router.get(
    "/commands/pending",
    response_model=List[AgentCommandRead],
    summary="Alias for polling pending commands for authenticated agent"
)
async def poll_agent_commands_alias(
    limit: int = Query(50, ge=1, le=100),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> List[AgentCommand]:
    return await AgentService.get_agent_pending_commands(
        current_agent, db, status_filter="pending", limit=limit
    )


@router.post(
    "/me/commands/{command_id}/ack",
    response_model=AgentCommandAckResponse,
    summary="Acknowledge command receipt by authenticated agent"
)
async def acknowledge_agent_command(
    command_id: int,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentCommandAckResponse:
    cmd = await AgentService.acknowledge_agent_command(current_agent, command_id, db)
    return AgentCommandAckResponse(
        command_id=cmd.id,
        status="acknowledged",
        message="Command successfully acknowledged by agent"
    )


@router.post(
    "/commands/{command_id}/ack",
    response_model=AgentCommandAckResponse,
    summary="Alias for acknowledging command receipt"
)
async def acknowledge_agent_command_alias(
    command_id: int,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentCommandAckResponse:
    cmd = await AgentService.acknowledge_agent_command(current_agent, command_id, db)
    return AgentCommandAckResponse(
        command_id=cmd.id,
        status="acknowledged",
        message="Command successfully acknowledged by agent"
    )


@router.post(
    "/me/commands/{command_id}/result",
    response_model=AgentCommandResultResponse,
    summary="Report command execution result by authenticated agent"
)
async def report_agent_command_result(
    command_id: int,
    req: AgentCommandResultRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentCommandResultResponse:
    cmd = await AgentService.report_agent_command_result(current_agent, command_id, req, db)
    return AgentCommandResultResponse(
        command_id=cmd.id,
        status=cmd.status,
        message=f"Command execution result recorded: {cmd.status}"
    )


@router.post(
    "/commands/{command_id}/result",
    response_model=AgentCommandResultResponse,
    summary="Alias for reporting command execution result"
)
async def report_agent_command_result_alias(
    command_id: int,
    req: AgentCommandResultRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
) -> AgentCommandResultResponse:
    cmd = await AgentService.report_agent_command_result(current_agent, command_id, req, db)
    return AgentCommandResultResponse(
        command_id=cmd.id,
        status=cmd.status,
        message=f"Command execution result recorded: {cmd.status}"
    )


@router.get(
    "",
    response_model=List[AgentRead],
    summary="List agents within tenant scope",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Agent]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AgentService.list_agents(skip, limit, db, scoped_org_id=scoped_org_id)


@router.get(
    "/{agent_id}",
    response_model=AgentRead,
    summary="Get agent details by ID (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def get_agent_by_id(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Agent:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AgentService.get_agent_by_id(agent_id, db, scoped_org_id=scoped_org_id)


@router.get(
    "/{agent_id}/telemetry",
    response_model=List[AgentTelemetryRead],
    summary="Get telemetry history for an agent (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def get_agent_telemetry(
    agent_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[AgentTelemetryRead]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AgentService.get_agent_telemetry(agent_id, skip, limit, db, scoped_org_id=scoped_org_id)


@router.get(
    "/{agent_id}/commands",
    response_model=List[AgentCommandRead],
    summary="List queued commands for an agent (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def get_agent_commands(
    agent_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[AgentCommand]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AgentService.get_agent_commands(agent_id, skip, limit, db, scoped_org_id=scoped_org_id)


@router.get(
    "/commands/{command_id}",
    response_model=AgentCommandRead,
    summary="Get single agent command by ID (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def get_agent_command_by_id(
    command_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AgentCommand:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await AgentService.get_command_by_id(command_id, db, scoped_org_id=scoped_org_id)
