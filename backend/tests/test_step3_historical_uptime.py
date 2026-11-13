"""
ServicePulse - Step 3 Historical Uptime & Outage Duration Tests
Verifies duration-based uptime calculations, maintenance window exclusions,
and insufficient data handling.
Author: Muhammadyusuf Usmonov
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.inventory import Device
from backend.app.models.monitoring import (
    MaintenanceWindow,
    OutageInterval,
)
from backend.app.models.network import NetworkCheck
from backend.app.models.organization import Organization
from backend.app.services.uptime_service import UptimeService


@pytest.mark.asyncio
async def test_duration_based_uptime_and_maintenance_exclusion(test_db: AsyncSession):
    """
    Verify:
    1. Newly created org with insufficient probes returns uptime_status='insufficient_data'.
    2. With sufficient observations, measured_uptime is accurately derived from duration.
    3. Planned maintenance window excludes overlapping outages from downtime penalty.
    """
    db = test_db

    # Create test organization
    org = Organization(name="Uptime Test Org", slug="uptime-test-org", max_devices=5)
    db.add(org)
    await db.flush()

    dev = Device(
        organization_id=org.id,
        name="Uptime Server",
        hostname="srv-uptime.local",
        ip_address="10.250.1.1",
        device_type="server",
        status="online",
        is_monitored=True,
        is_sample_data=True,
    )
    db.add(dev)
    await db.commit()

    org_id = org.id
    dev_id = dev.id

    # 1. Zero probes -> insufficient_data
    summary_empty = await UptimeService.get_organization_downtime_summary(org_id=org_id, window_days=30, db=db)
    assert summary_empty["uptime_status"] == "insufficient_data"
    assert summary_empty["measured_uptime_percent"] is None

    # 2. Add sufficient historical probe observations (15 checks)
    now = datetime.now(timezone.utc)
    for i in range(15):
        t = now - timedelta(days=1, hours=i)
        nc = NetworkCheck(
            device_id=dev_id,
            check_type="icmp_ping",
            is_successful=True,
            response_time_ms=1.5,
            packet_loss_percent=0.0,
            checked_at=t,
        )
        db.add(nc)
    await db.commit()

    # With no outages recorded, measured uptime should be 100.0%
    summary_clean = await UptimeService.get_organization_downtime_summary(org_id=org_id, window_days=30, db=db)
    assert summary_clean["uptime_status"] == "operational"
    assert summary_clean["measured_uptime_percent"] == 100.0
    assert summary_clean["total_downtime_minutes"] == 0.0

    # 3. Add an outage of 60 minutes
    o_start = now - timedelta(days=2)
    o_end = o_start + timedelta(minutes=60)
    outage = OutageInterval(
        organization_id=org_id,
        device_id=dev_id,
        started_at=o_start,
        ended_at=o_end,
        duration_seconds=3600.0,
        is_planned=False,
        root_cause="Switch power outage",
    )
    db.add(outage)
    await db.commit()

    summary_outage = await UptimeService.get_organization_downtime_summary(org_id=org_id, window_days=30, db=db)
    assert summary_outage["total_downtime_minutes"] == 60.0
    assert summary_outage["measured_uptime_percent"] < 100.0
    assert summary_outage["measured_uptime_percent"] > 99.0

    # 4. Add scheduled maintenance window covering the outage
    maint = MaintenanceWindow(
        organization_id=org_id,
        device_id=dev_id,
        title="Scheduled Firmware Upgrade",
        start_time=o_start - timedelta(minutes=10),
        end_time=o_end + timedelta(minutes=10),
        is_active=True,
    )
    db.add(maint)
    await db.commit()

    # Maintenance covers the outage -> downtime penalty should be excluded (0.0 minutes downtime)
    summary_maint = await UptimeService.get_organization_downtime_summary(org_id=org_id, window_days=30, db=db)
    assert summary_maint["total_downtime_minutes"] == 0.0
    assert summary_maint["measured_uptime_percent"] == 100.0
