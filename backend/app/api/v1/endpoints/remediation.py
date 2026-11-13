"""
ServicePulse - Automated Remediation Endpoints
Rules, execution tracking, and authorization verification.
Multi-tenant isolation enforced.
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
from backend.app.models.incident import Incident
from backend.app.models.inventory import Device
from backend.app.models.remediation import RemediationExecution, RemediationRule
from backend.app.models.user import User
from backend.app.schemas.remediation import (
    RemediationExecutionCreate,
    RemediationExecutionRead,
    RemediationRuleCreate,
    RemediationRuleRead,
)

router = APIRouter()

REMEDIATION_ROLES = ("platform_super_admin", "company_admin", "it_admin", "support", "admin")


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
    if exec_in.device_id is not None:
        dev_q = select(Device).where(Device.id == exec_in.device_id)
        dev = (await db.execute(dev_q)).scalar_one_or_none()
        if not dev or (scoped_org_id is not None and dev.organization_id != scoped_org_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device not found in your organization")

    execution = RemediationExecution(
        rule_id=exec_in.rule_id,
        incident_id=exec_in.incident_id,
        device_id=exec_in.device_id,
        status="executing",
        verification_status="pending",
        approved_by_user_id=current_user.id,
        execution_log=f"Triggered action '{rule.action_name}' by user {current_user.email}",
    )
    db.add(execution)
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
