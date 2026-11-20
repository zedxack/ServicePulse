"""
ServicePulse - Audit Log Inspection Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.audit import AuditLog
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogRead

router = APIRouter()


@router.get(
    "",
    response_model=List[AuditLogRead],
    summary="List audit records (tenant-isolated for company roles; global for platform admin)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[AuditLog]:
    scoped_org_id = get_user_tenant_org_id(current_user)

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    if scoped_org_id is not None:
        q = q.where(AuditLog.organization_id == scoped_org_id)
    if action:
        q = q.where(AuditLog.action == action.strip())

    result = await db.execute(q)
    return list(result.scalars().all())


@router.get(
    "/{audit_id}",
    response_model=AuditLogRead,
    summary="Retrieve single audit log entry by ID (tenant-scoped)",
    dependencies=[Depends(require_roles("platform_super_admin", "company_admin", "it_admin", "support", "admin"))]
)
async def get_audit_log_by_id(
    audit_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuditLog:
    scoped_org_id = get_user_tenant_org_id(current_user)

    q = select(AuditLog).where(AuditLog.id == audit_id)
    record = (await db.execute(q)).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")

    if scoped_org_id is not None and record.organization_id != scoped_org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")

    return record
