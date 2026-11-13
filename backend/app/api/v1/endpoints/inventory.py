"""
ServicePulse - Inventory Infrastructure Endpoints
Building -> Floor -> Room -> Device management and tree explorer
Multi-tenant isolation enforced.
Author: Muhammadyusuf Usmonov
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import (
    get_current_active_user,
    get_user_tenant_org_id,
    require_roles,
)
from backend.app.db.session import get_db
from backend.app.models.inventory import Building, Device, Floor, Room
from backend.app.models.network import NetworkCheck
from backend.app.models.user import User
from backend.app.schemas.inventory import (
    BuildingCreate,
    BuildingRead,
    BuildingUpdate,
    DeviceCreate,
    DeviceRead,
    DeviceUpdate,
    FloorCreate,
    FloorRead,
    InventoryTreeResponse,
    RoomCreate,
    RoomRead,
)
from backend.app.schemas.network import NetworkCheckRead
from backend.app.services.inventory_service import InventoryService

router = APIRouter()

INVENTORY_EDITORS = ("platform_super_admin", "company_admin", "it_admin", "admin", "support")
INVENTORY_DELETERS = ("platform_super_admin", "company_admin", "admin")


# -----------------------------------------------------------------------------
# Hierarchy Tree
# -----------------------------------------------------------------------------
@router.get(
    "/tree",
    response_model=InventoryTreeResponse,
    summary="Get complete organizational infrastructure hierarchy tree",
)
async def get_inventory_tree(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> InventoryTreeResponse:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.get_inventory_tree(db, scoped_org_id=scoped_org_id)


# -----------------------------------------------------------------------------
# Buildings
# -----------------------------------------------------------------------------
@router.get(
    "/buildings",
    response_model=List[BuildingRead],
    summary="List registered buildings",
)
async def list_buildings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Building]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.list_buildings(skip, limit, db, scoped_org_id=scoped_org_id)


@router.post(
    "/buildings",
    response_model=BuildingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new building",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def create_building(
    b_in: BuildingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Building:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.create_building(b_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/buildings/{building_id}",
    response_model=BuildingRead,
    summary="Get building details by ID",
)
async def get_building(
    building_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Building:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.get_building_by_id(building_id, db, scoped_org_id=scoped_org_id)


@router.patch(
    "/buildings/{building_id}",
    response_model=BuildingRead,
    summary="Update building details",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def update_building(
    building_id: int,
    b_in: BuildingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Building:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.update_building(building_id, b_in, current_user, db, scoped_org_id=scoped_org_id)


@router.delete(
    "/buildings/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete building (safeguarded against active devices)",
    dependencies=[Depends(require_roles(*INVENTORY_DELETERS))]
)
async def delete_building(
    building_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    scoped_org_id = get_user_tenant_org_id(current_user)
    await InventoryService.delete_building(building_id, current_user, db, scoped_org_id=scoped_org_id)


# -----------------------------------------------------------------------------
# Floors & Rooms
# -----------------------------------------------------------------------------
@router.post(
    "/floors",
    response_model=FloorRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a floor level to a building",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def create_floor(
    f_in: FloorCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Floor:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.create_floor(f_in, current_user, db, scoped_org_id=scoped_org_id)


@router.post(
    "/rooms",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a room to a floor",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def create_room(
    r_in: RoomCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Room:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.create_room(r_in, current_user, db, scoped_org_id=scoped_org_id)


# -----------------------------------------------------------------------------
# Devices
# -----------------------------------------------------------------------------
@router.get(
    "/devices",
    response_model=List[DeviceRead],
    summary="List devices with filtering and pagination",
)
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    device_type: Optional[str] = Query(None, description="Filter by server, workstation, router, switch, etc."),
    device_status: Optional[str] = Query(None, description="Filter by online, offline, warning, unknown"),
    room_id: Optional[int] = Query(None, description="Filter by room ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Device]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.list_devices(
        skip, limit, device_type, device_status, room_id, db, scoped_org_id=scoped_org_id
    )


@router.post(
    "/devices",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new device",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def create_device(
    d_in: DeviceCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Device:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.create_device(d_in, current_user, db, scoped_org_id=scoped_org_id)


@router.get(
    "/devices/{device_id}",
    response_model=DeviceRead,
    summary="Retrieve device details by ID",
)
async def get_device(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Device:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.get_device_by_id(device_id, db, scoped_org_id=scoped_org_id)


@router.get(
    "/devices/{device_id}/network-checks",
    response_model=List[NetworkCheckRead],
    summary="Retrieve network check probes for a device (tenant-scoped)",
)
async def get_device_network_checks(
    device_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[NetworkCheck]:
    scoped_org_id = get_user_tenant_org_id(current_user)
    await InventoryService.get_device_by_id(device_id, db, scoped_org_id=scoped_org_id)
    return await InventoryService.get_device_network_checks(device_id, skip, limit, db)


@router.patch(
    "/devices/{device_id}",
    response_model=DeviceRead,
    summary="Update device attributes",
    dependencies=[Depends(require_roles(*INVENTORY_EDITORS))]
)
async def update_device(
    device_id: int,
    d_in: DeviceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Device:
    scoped_org_id = get_user_tenant_org_id(current_user)
    return await InventoryService.update_device(device_id, d_in, current_user, db, scoped_org_id=scoped_org_id)


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Decommission/delete a device",
    dependencies=[Depends(require_roles(*INVENTORY_DELETERS))]
)
async def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    scoped_org_id = get_user_tenant_org_id(current_user)
    await InventoryService.delete_device(device_id, current_user, db, scoped_org_id=scoped_org_id)
