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
    organization_id: Optional[int] = None
    is_monitored: bool = True
    is_sample_data: bool = False


class DeviceCreate(DeviceBase):
    room_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    hostname: Optional[str] = Field(None, max_length=150)
    ip_address: Optional[str] = Field(None, max_length=45)
    mac_address: Optional[str] = Field(None, max_length=17)
    device_type: Optional[str] = Field(None, max_length=50)
    operating_system: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=30)
    is_monitored: Optional[bool] = None
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


class RoomUpdate(BaseModel):
    room_number: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    floor_id: Optional[int] = None


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


class FloorUpdate(BaseModel):
    level: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    building_id: Optional[int] = None


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
    organization_id: Optional[int] = None
    is_sample_data: bool = False


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class BuildingRead(BuildingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floors: List[FloorRead] = []
    created_at: datetime


class InventoryTreeResponse(BaseModel):
    total_buildings: int
    total_floors: int
    total_rooms: int
    total_devices: int
    buildings: List[BuildingRead]
