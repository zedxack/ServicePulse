"""
ServicePulse - Inventory Infrastructure Service
Building -> Floor -> Room -> Device hierarchy, CRUD, and deletion protection.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.audit import AuditLog
from backend.app.models.inventory import Building, Device, Floor, Room
from backend.app.models.network import NetworkCheck
from backend.app.models.user import User
from backend.app.schemas.inventory import (
    BuildingCreate,
    BuildingUpdate,
    DeviceCreate,
    DeviceUpdate,
    FloorCreate,
    InventoryTreeResponse,
    RoomCreate,
)


class InventoryService:
    # -------------------------------------------------------------------------
    # Buildings
    # -------------------------------------------------------------------------
    @staticmethod
    async def create_building(
        b_in: BuildingCreate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Building:
        target_org_id = scoped_org_id or actor.organization_id
        if b_in.organization_id and (actor.is_superuser or any(r.name == "platform_super_admin" for r in actor.roles)):
            target_org_id = b_in.organization_id

        q = select(Building).where(Building.code == b_in.code.strip().upper())
        if (await db.execute(q)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Building code '{b_in.code}' already exists")

        bld = Building(
            organization_id=target_org_id,
            name=b_in.name.strip(),
            code=b_in.code.strip().upper(),
            address=b_in.address,
            description=b_in.description,
            is_sample_data=b_in.is_sample_data,
        )
        db.add(bld)
        await db.flush()

        db.add(AuditLog(
            user_id=actor.id,
            organization_id=target_org_id,
            action="building_created",
            target_resource="building",
            target_id=str(bld.id),
            status="success",
            details=f"Created building {bld.name} ({bld.code})",
        ))
        await db.commit()
        return await InventoryService.get_building_by_id(bld.id, db)

    @staticmethod
    async def get_building_by_id(b_id: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> Building:
        q = select(Building).options(selectinload(Building.floors).selectinload(Floor.rooms).selectinload(Room.devices)).where(Building.id == b_id)
        b = (await db.execute(q)).scalar_one_or_none()
        if not b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
        if scoped_org_id is not None and b.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
        return b

    @staticmethod
    async def list_buildings(skip: int, limit: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> List[Building]:
        q = (
            select(Building)
            .options(selectinload(Building.floors).selectinload(Floor.rooms).selectinload(Room.devices))
            .order_by(Building.id)
            .offset(skip)
            .limit(limit)
        )
        if scoped_org_id is not None:
            q = q.where(Building.organization_id == scoped_org_id)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def update_building(
        b_id: int,
        b_in: BuildingUpdate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Building:
        b = await InventoryService.get_building_by_id(b_id, db, scoped_org_id=scoped_org_id)
        if b_in.name:
            b.name = b_in.name.strip()
        if b_in.code:
            code_upper = b_in.code.strip().upper()
            q = select(Building).where(Building.code == code_upper, Building.id != b_id)
            if (await db.execute(q)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building code already in use")
            b.code = code_upper
        if b_in.address is not None:
            b.address = b_in.address
        if b_in.description is not None:
            b.description = b_in.description

        db.add(b)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=b.organization_id,
            action="building_updated",
            target_resource="building",
            target_id=str(b.id),
            status="success",
            details=f"Updated building {b.id}",
        ))
        await db.commit()
        return await InventoryService.get_building_by_id(b_id, db)

    @staticmethod
    async def delete_building(b_id: int, actor: User, db: AsyncSession, scoped_org_id: Optional[int] = None) -> None:
        b = await InventoryService.get_building_by_id(b_id, db, scoped_org_id=scoped_org_id)
        # Safeguard: check active devices
        device_count = sum(len(room.devices) for floor in b.floors for room in floor.rooms)
        if device_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete building containing {device_count} active device(s). Reassign devices first."
            )

        await db.delete(b)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=b.organization_id,
            action="building_deleted",
            target_resource="building",
            target_id=str(b_id),
            status="success",
            details=f"Deleted building {b.name}",
        ))
        await db.commit()

    # -------------------------------------------------------------------------
    # Floors & Rooms
    # -------------------------------------------------------------------------
    @staticmethod
    async def create_floor(
        f_in: FloorCreate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Floor:
        # Check building exists and belongs to scoped org
        await InventoryService.get_building_by_id(f_in.building_id, db, scoped_org_id=scoped_org_id)
        floor = Floor(
            building_id=f_in.building_id,
            level=f_in.level,
            name=f_in.name.strip(),
            description=f_in.description,
            is_sample_data=f_in.is_sample_data,
        )
        db.add(floor)
        await db.commit()
        q = select(Floor).options(selectinload(Floor.rooms).selectinload(Room.devices)).where(Floor.id == floor.id)
        return (await db.execute(q)).scalar_one()

    @staticmethod
    async def create_room(
        r_in: RoomCreate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Room:
        # Check floor exists and belongs to building in scoped org
        q_floor = select(Floor).options(selectinload(Floor.building)).where(Floor.id == r_in.floor_id)
        floor = (await db.execute(q_floor)).scalar_one_or_none()
        if not floor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found")
        if scoped_org_id is not None and floor.building.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found")

        room = Room(
            floor_id=r_in.floor_id,
            room_number=r_in.room_number.strip(),
            name=r_in.name.strip(),
            description=r_in.description,
            is_sample_data=r_in.is_sample_data,
        )
        db.add(room)
        await db.commit()
        q = select(Room).options(selectinload(Room.devices)).where(Room.id == room.id)
        return (await db.execute(q)).scalar_one()

    # -------------------------------------------------------------------------
    # Devices
    # -------------------------------------------------------------------------
    @staticmethod
    async def create_device(
        d_in: DeviceCreate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Device:
        target_org_id = scoped_org_id or actor.organization_id
        if d_in.organization_id and (actor.is_superuser or any(r.name == "platform_super_admin" for r in actor.roles)):
            target_org_id = d_in.organization_id

        # Validate room if provided
        if d_in.room_id:
            q_room = (
                select(Room)
                .options(selectinload(Room.floor).selectinload(Floor.building))
                .where(Room.id == d_in.room_id)
            )
            room = (await db.execute(q_room)).scalar_one_or_none()
            if not room:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
            if target_org_id is not None and room.floor.building.organization_id != target_org_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room belongs to a different organization")

        dev = Device(
            organization_id=target_org_id,
            room_id=d_in.room_id,
            name=d_in.name.strip(),
            hostname=d_in.hostname.strip(),
            ip_address=d_in.ip_address.strip(),
            mac_address=d_in.mac_address.strip() if d_in.mac_address else None,
            device_type=d_in.device_type.strip().lower(),
            operating_system=d_in.operating_system,
            status="online",
            is_monitored=d_in.is_monitored,
            is_sample_data=d_in.is_sample_data,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(dev)
        await db.flush()

        db.add(AuditLog(
            user_id=actor.id,
            organization_id=target_org_id,
            action="device_created",
            target_resource="device",
            target_id=str(dev.id),
            status="success",
            details=f"Created device {dev.name} ({dev.ip_address})",
        ))
        await db.commit()
        return await InventoryService.get_device_by_id(dev.id, db)

    @staticmethod
    async def get_device_by_id(d_id: int, db: AsyncSession, scoped_org_id: Optional[int] = None) -> Device:
        q = select(Device).options(selectinload(Device.agent)).where(Device.id == d_id)
        dev = (await db.execute(q)).scalar_one_or_none()
        if not dev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        if scoped_org_id is not None and dev.organization_id != scoped_org_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return dev

    @staticmethod
    async def list_devices(
        skip: int,
        limit: int,
        device_type: Optional[str],
        device_status: Optional[str],
        room_id: Optional[int],
        db: AsyncSession,
        scoped_org_id: Optional[int] = None,
    ) -> List[Device]:
        q = select(Device).order_by(Device.id).offset(skip).limit(limit)
        if scoped_org_id is not None:
            q = q.where(Device.organization_id == scoped_org_id)
        if device_type:
            q = q.where(Device.device_type == device_type.strip().lower())
        if device_status:
            q = q.where(Device.status == device_status.strip().lower())
        if room_id:
            q = q.where(Device.room_id == room_id)
        return list((await db.execute(q)).scalars().all())

    @staticmethod
    async def update_device(
        d_id: int,
        d_in: DeviceUpdate,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> Device:
        dev = await InventoryService.get_device_by_id(d_id, db, scoped_org_id=scoped_org_id)
        if d_in.name is not None:
            dev.name = d_in.name.strip()
        if d_in.hostname is not None:
            dev.hostname = d_in.hostname.strip()
        if d_in.ip_address is not None:
            dev.ip_address = d_in.ip_address.strip()
        if d_in.mac_address is not None:
            dev.mac_address = d_in.mac_address.strip()
        if d_in.device_type is not None:
            dev.device_type = d_in.device_type.strip().lower()
        if d_in.operating_system is not None:
            dev.operating_system = d_in.operating_system
        if d_in.status is not None:
            dev.status = d_in.status.strip().lower()
        if d_in.is_monitored is not None:
            dev.is_monitored = d_in.is_monitored
        if d_in.room_id is not None:
            # Check room exists
            if d_in.room_id > 0:
                q_room = (
                    select(Room)
                    .options(selectinload(Room.floor).selectinload(Floor.building))
                    .where(Room.id == d_in.room_id)
                )
                room = (await db.execute(q_room)).scalar_one_or_none()
                if not room:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target room not found")
                if dev.organization_id is not None and room.floor.building.organization_id != dev.organization_id:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room belongs to a different organization")
                dev.room_id = d_in.room_id
            else:
                dev.room_id = None

        db.add(dev)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=dev.organization_id,
            action="device_updated",
            target_resource="device",
            target_id=str(dev.id),
            status="success",
            details=f"Updated device {dev.id}",
        ))
        await db.commit()
        return await InventoryService.get_device_by_id(d_id, db)

    @staticmethod
    async def delete_device(
        d_id: int,
        actor: User,
        db: AsyncSession,
        scoped_org_id: Optional[int] = None
    ) -> None:
        dev = await InventoryService.get_device_by_id(d_id, db, scoped_org_id=scoped_org_id)
        await db.delete(dev)
        db.add(AuditLog(
            user_id=actor.id,
            organization_id=dev.organization_id,
            action="device_deleted",
            target_resource="device",
            target_id=str(d_id),
            status="success",
            details=f"Deleted device {dev.name}",
        ))
        await db.commit()

    @staticmethod
    async def get_device_network_checks(
        device_id: int,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> List[NetworkCheck]:
        q = (
            select(NetworkCheck)
            .where(NetworkCheck.device_id == device_id)
            .order_by(NetworkCheck.checked_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list((await db.execute(q)).scalars().all())

    # -------------------------------------------------------------------------
    # Hierarchy Tree
    # -------------------------------------------------------------------------
    @staticmethod
    async def get_inventory_tree(db: AsyncSession, scoped_org_id: Optional[int] = None) -> InventoryTreeResponse:
        buildings_q = (
            select(Building)
            .options(
                selectinload(Building.floors)
                .selectinload(Floor.rooms)
                .selectinload(Room.devices)
            )
            .order_by(Building.id)
        )
        if scoped_org_id is not None:
            buildings_q = buildings_q.where(Building.organization_id == scoped_org_id)
        buildings = list((await db.execute(buildings_q)).scalars().all())

        total_bld = len(buildings)
        total_fl = sum(len(b.floors) for b in buildings)
        total_rm = sum(len(f.rooms) for b in buildings for f in b.floors)
        total_dev = sum(len(r.devices) for b in buildings for f in b.floors for r in f.rooms)

        return InventoryTreeResponse(
            total_buildings=total_bld,
            total_floors=total_fl,
            total_rooms=total_rm,
            total_devices=total_dev,
            buildings=buildings,
        )
