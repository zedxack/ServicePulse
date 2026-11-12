"""
ServicePulse - Health Check Schemas
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    timestamp: datetime
    database_status: str = Field(..., json_schema_extra={"example": "connected"})
