"""
ServicePulse - Audit Log Pydantic Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    target_resource: str
    target_id: Optional[str] = None
    status: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
