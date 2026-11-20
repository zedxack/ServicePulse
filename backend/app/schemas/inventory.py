"""
ServicePulse - Inventory Infrastructure Schemas
Pydantic v2
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

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


# -----------------------------------------------------------------------------
# Stage 6: Fleet Automation — Subnet Discovery, Bulk Import, Remote Actions
# -----------------------------------------------------------------------------
class SubnetDiscoveryRequest(BaseModel):
    subnet_cidr: str = Field(..., description="Target subnet in CIDR notation, e.g. 192.168.10.0/24")
    room_id: Optional[int] = Field(None, description="Optional target room ID")
    scan_mode: str = Field("fast", description="Scan mode: fast or deep")


class DiscoveredCandidate(BaseModel):
    ip_address: str
    hostname: str
    mac_address: str
    detected_device_type: str = "workstation"
    open_ports: List[int] = []
    response_time_ms: float = 0.0
    already_registered: bool = False


class SubnetDiscoveryResponse(BaseModel):
    subnet_cidr: str
    total_probed: int
    discovered_count: int
    candidates: List[DiscoveredCandidate]
    scan_duration_ms: float


class DiscoveredNodeImportItem(BaseModel):
    ip_address: str
    hostname: str
    mac_address: Optional[str] = None
    device_type: str = "workstation"
    room_id: Optional[int] = None
    operating_system: Optional[str] = None


class DiscoveredBulkImportRequest(BaseModel):
    room_id: Optional[int] = None
    devices: List[DiscoveredNodeImportItem]


class DiscoveredBulkImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    created_device_ids: List[int]
    message: str


class RemoteActionRequest(BaseModel):
    action: str = Field(..., description="Allowlisted action: restart_service, kill_process, flush_dns, collect_diagnostics, quarantine_network")
    parameters: Optional[Dict[str, Any]] = None
    is_simulation: bool = False


class RemoteActionResponse(BaseModel):
    command_id: int
    device_id: int
    action: str
    status: str
    verification_status: str
    execution_result: str
    executed_at: datetime


class ProcessItem(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    ram_mb: float


class SystemServiceItem(BaseModel):
    name: str
    display_name: str
    status: str  # RUNNING or STOPPED
    can_restart: bool = True


class DeviceProcessSnapshotResponse(BaseModel):
    device_id: int
    device_name: str
    os_name: Optional[str] = None
    captured_at: datetime
    top_processes: List[ProcessItem]
    system_services: List[SystemServiceItem]

