"""
ServicePulse - Step 3 Historical Uptime & Outage Duration Tests
Verifies duration-based uptime calculations, maintenance window exclusions,
exact interval intersections, overlapping window merging, and boundary clipping.
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
from backend.app.services.uptime_service import (
    UptimeService,
    merge_intervals,
)


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


def test_merge_intervals_utility():
    """Verify merging of overlapping, contiguous, and disjoint time intervals."""
    t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 1, 10, 45, tzinfo=timezone.utc)
    t3 = datetime(2026, 11, 1, 11, 15, tzinfo=timezone.utc)
    t4 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    t5 = datetime(2026, 11, 1, 12, 30, tzinfo=timezone.utc)

    # Overlapping intervals: [10:00-10:45] and [10:30-11:15] -> [10:00-11:15]
    merged = merge_intervals([(t0, t2), (t1, t3)])
    assert len(merged) == 1
    assert merged[0] == (t0, t3)

    # Disjoint intervals: [10:00-10:30] and [12:00-12:30] -> remains 2 intervals
    disjoint = merge_intervals([(t0, t1), (t4, t5)])
    assert len(disjoint) == 2
    assert disjoint[0] == (t0, t1)
    assert disjoint[1] == (t4, t5)

    # Empty list
    assert merge_intervals([]) == []


def test_maintenance_window_intersection_calculations():
    """
    Test direct mathematical intersection rules:
    - Full containment
    - Partial overlap at beginning
    - Partial overlap at end
    - Multiple overlapping windows without double counting
    - No overlap
    - Outage extending beyond reporting window
    """
    now = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=30)
    w_end = now

    # Target outage: 10:00 to 11:00 (3600 seconds = 60 minutes)
    out_s = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    out_e = datetime(2026, 11, 10, 11, 0, tzinfo=timezone.utc)

    # Case 1: Full Containment (Maint: 09:30 to 11:30)
    maint_full = [(out_s - timedelta(minutes=30), out_e + timedelta(minutes=30))]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_s, out_e, False, maint_full, w_start, w_end
    )
    assert tot == 3600.0
    assert maint == 3600.0
    assert unp == 0.0

    # Case 2: Partial Overlap at Beginning (Maint: 09:30 to 10:20 -> 20 min overlap)
    maint_start = [(out_s - timedelta(minutes=30), out_s + timedelta(minutes=20))]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_s, out_e, False, maint_start, w_start, w_end
    )
    assert tot == 3600.0
    assert maint == 1200.0  # 20 minutes
    assert unp == 2400.0   # 40 minutes unplanned

    # Case 3: Partial Overlap at End (Maint: 10:45 to 11:30 -> 15 min overlap)
    maint_end = [(out_s + timedelta(minutes=45), out_e + timedelta(minutes=30))]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_s, out_e, False, maint_end, w_start, w_end
    )
    assert tot == 3600.0
    assert maint == 900.0   # 15 minutes
    assert unp == 2700.0   # 45 minutes unplanned

    # Case 4: Multiple Overlapping Windows (Maint1: 10:10-10:40, Maint2: 10:30-10:50)
    # Merged overlap is 10:10 to 10:50 (40 minutes = 2400s) -> no double counting
    maint_multi = [
        (out_s + timedelta(minutes=10), out_s + timedelta(minutes=40)),
        (out_s + timedelta(minutes=30), out_s + timedelta(minutes=50)),
    ]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_s, out_e, False, maint_multi, w_start, w_end
    )
    assert tot == 3600.0
    assert maint == 2400.0  # 40 minutes merged
    assert unp == 1200.0   # 20 minutes unplanned

    # Case 5: No Overlap (Maint: 11:15 to 12:00)
    maint_none = [(out_e + timedelta(minutes=15), out_e + timedelta(minutes=60))]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_s, out_e, False, maint_none, w_start, w_end
    )
    assert tot == 3600.0
    assert maint == 0.0
    assert unp == 3600.0

    # Case 6: Outage extending beyond reporting window
    # Window: 30 days. Outage: 35 days ago to 25 days ago (10 days total)
    # Clipped outage inside window is 5 days (from 30 days ago to 25 days ago = 432,000s)
    # Maintenance: 28 days ago to 26 days ago (2 days = 172,800s)
    out_old = now - timedelta(days=35)
    out_mid = now - timedelta(days=25)
    maint_windowed = [(now - timedelta(days=28), now - timedelta(days=26))]
    tot, maint, unp = UptimeService.calculate_unplanned_outage_downtime(
        out_old, out_mid, False, maint_windowed, w_start, w_end
    )
    assert tot == 5 * 86400.0  # Exactly 5 clipped days
    assert maint == 2 * 86400.0  # Exactly 2 days maintenance
    assert unp == 3 * 86400.0   # Exactly 3 days unplanned downtime


@pytest.mark.asyncio
async def test_database_integrated_maintenance_intersections(test_db: AsyncSession):
    """
    End-to-end integration test with database models:
    Verifies that multiple maintenance windows with partial overlap and window clipping
    produce accurate total_downtime_minutes and uptime percentages.
    """
    db = test_db
    now = datetime.now(timezone.utc)

    org = Organization(name="Overlap Org", slug="overlap-org", max_devices=2)
    db.add(org)
    await db.flush()

    dev = Device(
        organization_id=org.id,
        name="Switch-Core-01",
        hostname="sw01.local",
        ip_address="10.100.1.1",
        device_type="switch",
        status="online",
        is_monitored=True,
        is_sample_data=False,
    )
    db.add(dev)
    await db.commit()

    # Seed 15 network checks to ensure sufficient observations
    for i in range(15):
        db.add(NetworkCheck(
            device_id=dev.id,
            check_type="icmp_ping",
            is_successful=True,
            response_time_ms=2.0,
            packet_loss_percent=0.0,
            checked_at=now - timedelta(days=1, hours=i),
        ))

    # Outage of 100 minutes (now - 200 min to now - 100 min)
    out_start = now - timedelta(minutes=200)
    out_end = now - timedelta(minutes=100)
    outage = OutageInterval(
        organization_id=org.id,
        device_id=dev.id,
        started_at=out_start,
        ended_at=out_end,
        duration_seconds=6000.0,
        is_planned=False,
        root_cause="Link failure",
    )
    db.add(outage)

    # Window 1: Overlaps minutes 10 to 40 of the outage (30 mins)
    mw1 = MaintenanceWindow(
        organization_id=org.id,
        device_id=dev.id,
        title="MW 1",
        start_time=out_start + timedelta(minutes=10),
        end_time=out_start + timedelta(minutes=40),
        is_active=True,
    )
    # Window 2: Overlaps minutes 30 to 60 of the outage (30 mins, overlapping MW1 by 10 mins)
    mw2 = MaintenanceWindow(
        organization_id=org.id,
        device_id=dev.id,
        title="MW 2",
        start_time=out_start + timedelta(minutes=30),
        end_time=out_start + timedelta(minutes=60),
        is_active=True,
    )
    db.add(mw1)
    db.add(mw2)
    await db.commit()

    # Merged maintenance is from minute 10 to minute 60 = 50 minutes.
    # Outage total is 100 minutes.
    # Expected unplanned downtime: 100 - 50 = 50 minutes.
    summary = await UptimeService.get_organization_downtime_summary(org_id=org.id, window_days=30, db=db)
    assert summary["uptime_status"] == "operational"
    assert summary["total_downtime_minutes"] == 50.0
