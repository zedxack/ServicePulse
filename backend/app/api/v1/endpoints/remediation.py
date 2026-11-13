"""
ServicePulse - Automated Remediation Endpoints
Rules, execution tracking, approval workflows, and verification.
Multi-tenant isolation and strict action allowlisting enforced.
Author: Muhammadyusuf Usmonov
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.agent import Agent, AgentCommand
from backend.app.models.incident import Incident
from backend.app.models.inventory import Device
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.models.user import User
from backend.app.schemas.remediation import (
    RemediationApprovalRequest,
    RemediationExecutionCreate,
    RemediationExecutionRead,
    RemediationRuleCreate,
    RemediationRuleRead,
)
from backend.app.services.remediation_policy import RemediationPolicy
from backend.app.services.remediation_service import RemediationService
from backend.app.services.remediation_verification import RemediationVerification

router = APIRouter()

REMEDIATION_ROLES = ("platform_super_admin", "company_admin", "it_admin", "support", "admin")
REMEDIATION_APPROVERS = ("platform_super_admin", "company_admin", "it_admin", "admin")


@router.post(
    "/rules",
    response_model=RemediationRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create automated remediation rule (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def create_remediation_rule(
    rule_in: RemediationRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationRule:
    # Validate action is allowlisted and parameters conform to schema
    is_valid, err, _ = RemediationPolicy.validate_action(rule_in.action_name, rule_in.action_parameters)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    scoped_org_id = get_user_tenant_org_id(current_user)
    target_org_id = scoped_org_id or current_user.organization_id
    rule = RemediationRule(
        organization_id=target_org_id,
        name=rule_in.name.strip(),
        description=rule_in.description,
        trigger_condition=rule_in.trigger_condition.strip(),
        target_device_type=rule_in.target_device_type,
        action_name=rule_in.action_name.strip(),
        action_parameters=rule_in.action_parameters,
        is_active=rule_in.is_active,
        requires_approval=rule_in.requires_approval,
        max_retries=rule_in.max_retries,
        cooldown_seconds=rule_in.cooldown_seconds,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get(
    "/rules",
    response_model=List[RemediationRuleRead],
    summary="List automated remediation rules (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def list_remediation_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[RemediationRule]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = select(RemediationRule).order_by(RemediationRule.id).offset(skip).limit(limit)
    if scoped_org_id is not None:
        q = q.where(RemediationRule.organization_id == scoped_org_id)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get(
    "/rules/{rule_id}",
    response_model=RemediationRuleRead,
    summary="Get single remediation rule by ID (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def get_remediation_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationRule:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = select(RemediationRule).where(RemediationRule.id == rule_id)
    rule = (await db.execute(q)).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation rule not found")
    if scoped_org_id is not None and rule.organization_id != scoped_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation rule not found")
    return rule


@router.post(
    "/executions",
    response_model=RemediationExecutionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger or record a remediation execution (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def create_remediation_execution(
    exec_in: RemediationExecutionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationExecution:
    scoped_org_id = get_user_tenant_org_id(current_user)

    # 1. Validate parent rule ownership
    rule_q = select(RemediationRule).where(RemediationRule.id == exec_in.rule_id)
    rule = (await db.execute(rule_q)).scalar_one_or_none()
    if not rule or (scoped_org_id is not None and rule.organization_id != scoped_org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation rule not found in your organization")

    # 2. Validate parent incident ownership
    inc_q = select(Incident).where(Incident.id == exec_in.incident_id)
    incident = (await db.execute(inc_q)).scalar_one_or_none()
    if not incident or (scoped_org_id is not None and incident.organization_id != scoped_org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found in your organization")

    # 3. If device_id provided, validate device ownership
    dev = None
    if exec_in.device_id is not None:
        dev_q = select(Device).where(Device.id == exec_in.device_id)
        dev = (await db.execute(dev_q)).scalar_one_or_none()
        if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device not found in your organization")

    is_sim = exec_in.is_simulation or (dev.is_sample_data if dev else False)
    status_str = "pending_approval" if rule.requires_approval else "executing"

    execution = RemediationExecution(
        rule_id=exec_in.rule_id,
        incident_id=exec_in.incident_id,
        device_id=exec_in.device_id,
        status=status_str,
        verification_status="pending",
        is_simulation=is_sim,
        approved_by_user_id=current_user.id if not rule.requires_approval else None,
        execution_log=f"Triggered action '{rule.action_name}' by user {current_user.email}",
    )
    db.add(execution)
    await db.flush()

    # If execution does not require approval and device has an agent, queue AgentCommand
    if not rule.requires_approval and dev:
        agent_q = select(Agent).where(Agent.device_id == dev.id)
        agent = (await db.execute(agent_q)).scalar_one_or_none()
        if agent:
            cmd = AgentCommand(
                agent_id=agent.id,
                device_id=dev.id,
                action_name=rule.action_name,
                parameters=rule.action_parameters,
                status="pending",
                verification_status="pending",
                is_simulation=is_sim,
                remediation_execution_id=execution.id,
                requested_by_user_id=current_user.id,
            )
            db.add(cmd)
            await db.flush()
            execution.agent_command_id = cmd.id

    await db.commit()
    await db.refresh(execution)
    return execution


@router.get(
    "/executions",
    response_model=List[RemediationExecutionRead],
    summary="List remediation execution audit log (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def list_remediation_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[RemediationExecution]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = (
        select(RemediationExecution)
        .join(Incident, RemediationExecution.incident_id == Incident.id)
        .order_by(RemediationExecution.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if scoped_org_id is not None:
        q = q.where(Incident.organization_id == scoped_org_id)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get(
    "/executions/{execution_id}",
    response_model=RemediationExecutionRead,
    summary="Get remediation execution details by ID (tenant-scoped)",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def get_remediation_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationExecution:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = (
        select(RemediationExecution)
        .options(
            selectinload(RemediationExecution.incident),
            selectinload(RemediationExecution.rule)
        )
        .where(RemediationExecution.id == execution_id)
    )
    exc = (await db.execute(q)).scalar_one_or_none()
    if not exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation execution not found")

    # Verify ownership through incident or rule organization
    exc_org = None
    if exc.incident:
        exc_org = exc.incident.organization_id
    elif exc.rule:
        exc_org = exc.rule.organization_id

    if scoped_org_id is not None and exc_org != scoped_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation execution not found")

    return exc


@router.post(
    "/executions/{execution_id}/approve",
    response_model=RemediationExecutionRead,
    summary="Approve pending remediation execution and dispatch command",
    dependencies=[Depends(require_roles(*REMEDIATION_APPROVERS))]
)
async def approve_remediation_execution(
    execution_id: int,
    app_in: RemediationApprovalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationExecution:
    scoped_org_id = get_user_tenant_org_id(current_user)
    # Check tenant ownership first
    q = select(RemediationExecution).options(selectinload(RemediationExecution.incident)).where(RemediationExecution.id == execution_id)
    exc = (await db.execute(q)).scalar_one_or_none()
    if not exc or (scoped_org_id is not None and exc.incident and exc.incident.organization_id != scoped_org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation execution not found")

    try:
        return await RemediationService.approve_execution(
            execution_id=execution_id,
            approver=current_user,
            review_notes=app_in.review_notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/executions/{execution_id}/reject",
    response_model=RemediationExecutionRead,
    summary="Reject pending remediation execution",
    dependencies=[Depends(require_roles(*REMEDIATION_APPROVERS))]
)
async def reject_remediation_execution(
    execution_id: int,
    app_in: RemediationApprovalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationExecution:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = select(RemediationExecution).options(selectinload(RemediationExecution.incident)).where(RemediationExecution.id == execution_id)
    exc = (await db.execute(q)).scalar_one_or_none()
    if not exc or (scoped_org_id is not None and exc.incident and exc.incident.organization_id != scoped_org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation execution not found")

    try:
        return await RemediationService.reject_execution(
            execution_id=execution_id,
            reviewer=current_user,
            review_notes=app_in.review_notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/executions/{execution_id}/verify",
    response_model=RemediationExecutionRead,
    summary="Trigger independent verification check for an execution",
    dependencies=[Depends(require_roles(*REMEDIATION_ROLES))]
)
async def verify_remediation_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> RemediationExecution:
    scoped_org_id = get_user_tenant_org_id(current_user)
    q = select(RemediationExecution).options(selectinload(RemediationExecution.incident)).where(RemediationExecution.id == execution_id)
    exc = (await db.execute(q)).scalar_one_or_none()
    if not exc or (scoped_org_id is not None and exc.incident and exc.incident.organization_id != scoped_org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remediation execution not found")

    verified, log_msg = await RemediationVerification.verify_execution(execution_id, db)
    await db.refresh(exc)
    return exc
