"""
ServicePulse - Alert Center & In-App Notification Endpoints
Author: Muhammadyusuf Usmonov
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_active_user, get_user_tenant_org_id
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.notification import (
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)
from backend.app.services.notification_service import NotificationService

router = APIRouter()


class MarkAllReadResponse(BaseModel):
    updated: int
    updated_count: int = 0


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List in-app alert notifications (tenant & role-scoped)",
)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None, description="Filter by info, warning, critical"),
    category: Optional[str] = Query(None, description="Filter by device, incident, remediation, software"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    total, unread, items = await NotificationService.list_notifications(
        current_user=current_user,
        skip=skip,
        limit=limit,
        severity=severity,
        category=category,
        is_read=is_read,
        db=db,
        scoped_org_id=scoped_org_id,
    )
    return NotificationListResponse(total=total, unread_count=unread, items=items)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get count of unread alert notifications for badge indicator",
)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    count = await NotificationService.get_unread_count(
        current_user=current_user, db=db, scoped_org_id=scoped_org_id
    )
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{alert_id}/read",
    response_model=NotificationRead,
    summary="Mark single alert notification as read",
)
async def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await NotificationService.mark_as_read(
        alert_id=alert_id,
        current_user=current_user,
        db=db,
        scoped_org_id=scoped_org_id,
    )


@router.post(
    "/mark-all-read",
    response_model=MarkAllReadResponse,
    summary="Mark all visible unread notifications as read",
)
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    updated = await NotificationService.mark_all_as_read(
        current_user=current_user,
        db=db,
        scoped_org_id=scoped_org_id,
    )
    return MarkAllReadResponse(updated=updated, updated_count=updated)
