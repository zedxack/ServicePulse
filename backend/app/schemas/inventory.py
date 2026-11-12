"""
ServicePulse - Inventory Infrastructure Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviceBase(BaseModel):
    name: str = Field(..., max_length=150)
    hostname: str = Field(..., max_length=150)
    ip_address: str = Field(..., max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    device_type: str = Field("workstation", max_length=50)
    operating_system: Optional[str] = Field(None, max_length=100)
    is_monitored: bool = True
    is_sample_data: bool = False


class DeviceCreate(DeviceBase):
    room_id: Optional[int] = None


class DeviceRead(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: Optional[int] = None
    status: str
    last_seen: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    consecutive_failures: int = 0
    created_at: datetime


class RoomBase(BaseModel):
    room_number: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_sample_data: bool = False


class RoomCreate(RoomBase):
    floor_id: int


class RoomRead(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor_id: int
    devices: List[DeviceRead] = []
    created_at: datetime


class FloorBase(BaseModel):
    level: int
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_sample_data: bool = False


class FloorCreate(FloorBase):
    building_id: int


class FloorRead(FloorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    rooms: List[RoomRead] = []
    created_at: datetime


class BuildingBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_sample_data: bool = False


class BuildingCreate(BuildingBase):
    pass


class BuildingRead(BuildingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floors: List[FloorRead] = []
    created_at: datetime


class InventoryTreeResponse(BaseModel):
    buildings: List[BuildingRead]
