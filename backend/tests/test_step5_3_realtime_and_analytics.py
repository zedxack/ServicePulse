"""
ServicePulse - STEP 5.3 Real-Time Monitoring, Analytics & Alert Center Tests
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.inventory import Device
from backend.app.models.network import NetworkCheck
from backend.app.schemas.notification import NotificationCreate
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.notification_service import NotificationService
from backend.app.services.uptime_service import (
    calculate_interval_intersection_duration,
    merge_intervals,
)
from backend.app.services.ws_manager import ConnectionManager, WSTicketStore


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ==============================================================================
# MODULE 5.3.1: WEBSOCKET TICKETS & ISOLATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_ws_ticket_store_lifecycle():
    """Verify single-use property and expiration of WebSocket connection tickets."""
    store = WSTicketStore(default_ttl_seconds=2)

    # 1. Issue ticket
    ticket = await store.create_ticket(
        user_id=42,
        organization_id=10,
        roles=["it_admin"],
        email="test@servicepulse.uz",
        ttl_seconds=2,
    )
    assert isinstance(ticket, str) and len(ticket) >= 32

    # 2. First redemption succeeds
    ctx = await store.redeem_ticket(ticket)
    assert ctx is not None
    assert ctx.user_id == 42
    assert ctx.organization_id == 10
    assert "it_admin" in ctx.roles
    assert ctx.email == "test@servicepulse.uz"

    # 3. Second redemption fails (strictly single-use)
    ctx_reuse = await store.redeem_ticket(ticket)
    assert ctx_reuse is None

    # 4. Expired ticket fails
    ticket_expired = await store.create_ticket(
        user_id=99,
        organization_id=1,
        roles=["platform_super_admin"],
        email="super@servicepulse.uz",
        ttl_seconds=1,
    )
    await asyncio.sleep(1.2)
    ctx_expired = await store.redeem_ticket(ticket_expired)
    assert ctx_expired is None


@pytest.mark.asyncio
async def test_ws_ticket_endpoint_auth(client: AsyncClient):
    """Verify POST /api/v1/ws/ticket requires authenticated bearer token and returns ticket."""
    # Unauthenticated request rejected
    res_unauth = await client.post("/api/v1/ws/ticket")
    assert res_unauth.status_code == 401

    # Authenticated superuser request
    super_tok = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    res_auth = await client.post("/api/v1/ws/ticket", headers={"Authorization": f"Bearer {super_tok}"})
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert "ticket" in data
    assert data["expires_in"] == 30
    assert data["expires_in_seconds"] == 30
    assert len(data["ticket"]) >= 32


@pytest.mark.asyncio
async def test_ws_connection_manager_tenant_isolation():
    """Verify ConnectionManager enforces cross-tenant event isolation and superuser broadcasts."""
    manager = ConnectionManager()

    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def accept(self):
            pass

        async def send_text(self, text: str):
            self.sent_messages.append(text)

    ws_org1 = MockWebSocket()
    ws_org2 = MockWebSocket()
    ws_super = MockWebSocket()

    # Register connections
    c1 = await manager.connect(
        websocket=ws_org1,
        user_id=1,
        organization_id=10,
        roles=["it_admin"],
        email="user1@org10.uz",
    )
    c2 = await manager.connect(
        websocket=ws_org2,
        user_id=2,
        organization_id=20,
        roles=["it_admin"],
        email="user2@org20.uz",
    )
    c_super = await manager.connect(
        websocket=ws_super,
        user_id=99,
        organization_id=None,
        roles=["platform_super_admin"],
        email="admin@global.uz",
    )

    # Broadcast event to Org 10
    await manager.broadcast_to_org(10, "device:status_change", {"device_id": 1, "status": "offline"})

    # Org 10 and Superuser receive; Org 20 MUST NOT receive
    assert len(ws_org1.sent_messages) == 1
    assert "device:status_change" in ws_org1.sent_messages[0]
    assert len(ws_super.sent_messages) == 1
    assert len(ws_org2.sent_messages) == 0

    # Broadcast to Org 20
    await manager.broadcast_to_org(20, "incident:created", {"id": 105})

    assert len(ws_org2.sent_messages) == 1
    assert "incident:created" in ws_org2.sent_messages[0]
    assert len(ws_org1.sent_messages) == 1  # Unchanged
    assert len(ws_super.sent_messages) == 2  # Received second event

    # Clean up
    await manager.disconnect(c1)
    await manager.disconnect(c2)
    await manager.disconnect(c_super)


# ==============================================================================
# MODULE 5.3.2: DURATION-BASED SLA & ANALYTICS TESTS
# ==============================================================================


def test_sla_duration_calculation_unit():
    """Verify exact mathematical duration calculation with overlapping deduplication."""
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(days=1)

    # Outage 1: 10:00 to 11:00 (60 mins)
    o1_start = t0 + timedelta(hours=10)
    o1_end = t0 + timedelta(hours=11)

    # Outage 2: 10:30 to 11:30 (overlaps with o1, extending by 30 mins)
    o2_start = t0 + timedelta(hours=10, minutes=30)
    o2_end = t0 + timedelta(hours=11, minutes=30)

    # Overlapping interval merge: [10:00, 11:30] = 90 mins = 5400s (NOT 120 mins)
    merged = merge_intervals([
        (o1_start, o1_end),
        (o2_start, o2_end),
    ])
    assert len(merged) == 1
    assert (merged[0][1] - merged[0][0]).total_seconds() == 5400.0


def test_sla_maintenance_window_exclusion_unit():
    """Verify that unavailability inside a scheduled maintenance window is excluded from SLA penalty."""
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(days=1)

    # Scheduled maintenance: 02:00 to 04:00 (2 hours)
    m_start = t0 + timedelta(hours=2)
    m_end = t0 + timedelta(hours=4)

    # Outage entirely during maintenance: 02:30 to 03:30 (1 hour)
    o_start = t0 + timedelta(hours=2, minutes=30)
    o_end = t0 + timedelta(hours=3, minutes=30)

    # Overlap between outage and maintenance window
    overlap = calculate_interval_intersection_duration(
        o_start,
        o_end,
        [(m_start, m_end)],
    )
    # The 1-hour outage is completely inside the 2-hour window => 3600.0s overlap
    assert overlap == 3600.0
    unplanned_downtime = max(0.0, (o_end - o_start).total_seconds() - overlap)
    assert unplanned_downtime == 0.0


@pytest.mark.asyncio
async def test_sla_insufficient_data_threshold(test_db: AsyncSession):
    """Verify that fewer than 10 probe observations yields 'insufficient_data' with zero fabricated metrics."""
    dev = Device(
        organization_id=1,
        name="Test Sensor 01",
        hostname="test-sensor-01",
        device_type="sensor",
        ip_address="10.0.0.99",
        status="online",
        is_monitored=True,
    )
    test_db.add(dev)
    await test_db.flush()

    now = datetime.now(timezone.utc)
    for i in range(2):
        nc = NetworkCheck(
            device_id=dev.id,
            check_type="icmp",
            is_successful=True,
            response_time_ms=10.0,
            checked_at=now - timedelta(minutes=i * 5),
        )
        test_db.add(nc)
    await test_db.commit()

    sla = await AnalyticsService.get_sla_overview(
        org_id=1,
        days=7,
        db=test_db,
    )

    # Strict adherence: insufficient data MUST NOT produce synthetic 100% or fabricated numbers
    assert sla.uptime_status == "insufficient_data"
    assert sla.measured_uptime_percent is None
    assert sla.is_sla_met is None


@pytest.mark.asyncio
async def test_analytics_endpoints_integration(client: AsyncClient, test_db: AsyncSession):
    """Verify GET /api/v1/analytics/sla and trend endpoints via HTTP client."""
    super_tok = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    headers = {"Authorization": f"Bearer {super_tok}"}

    # 1. SLA Overview
    res_sla = await client.get("/api/v1/analytics/sla?period_days=30", headers=headers)
    assert res_sla.status_code == 200
    sla_data = res_sla.json()
    assert "observation_window_days" in sla_data
    assert "sla_target_percent" in sla_data
    assert "uptime_status" in sla_data
    assert sla_data["observation_window_days"] == 30

    # 2. Availability Trend
    res_avail = await client.get("/api/v1/analytics/availability-trend?period_days=7", headers=headers)
    assert res_avail.status_code == 200
    avail_data = res_avail.json()
    assert "points" in avail_data
    assert len(avail_data["points"]) <= 7

    # 3. Incident Trends
    res_inc = await client.get("/api/v1/analytics/incident-trends?period_days=7", headers=headers)
    assert res_inc.status_code == 200
    inc_data = res_inc.json()
    assert "points" in inc_data
    assert "total_incidents" in inc_data


# ==============================================================================
# MODULE 5.3.3: IN-APP ALERTS & NOTIFICATIONS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_notification_creation_and_deduplication(test_db: AsyncSession):
    """Verify Notification creation, fingerprint hashing, and 15-minute cooldown deduplication."""
    notif_in = NotificationCreate(
        organization_id=1,
        title="Router High Temperature",
        message="Core router ambient temperature exceeded 65C.",
        severity="warning",
        category="device",
        fingerprint="temp_warning_r01",
        data={"temp": 67.2},
    )

    # 1. Initial creation
    n1 = await NotificationService.create_notification(test_db, notif_in)
    assert n1.id is not None
    assert n1.is_read is False

    # 2. Duplicate within cooldown window returns existing instance without creating another
    n2 = await NotificationService.create_notification(test_db, notif_in)
    assert n2.id == n1.id


@pytest.mark.asyncio
async def test_alerts_endpoints_and_cross_tenant_isolation(client: AsyncClient, test_db: AsyncSession):
    """Verify notifications endpoints: listing, mark read, mark all read, and cross-tenant scoping."""
    super_tok = await get_token(client, settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD)
    super_h = {"Authorization": f"Bearer {super_tok}"}

    # 1. Create two tenant orgs
    res_a = await client.post("/api/v1/organizations", json={"name": "Alert Org A", "slug": "alert-org-a"}, headers=super_h)
    org_a = res_a.json()["id"]

    res_b = await client.post("/api/v1/organizations", json={"name": "Alert Org B", "slug": "alert-org-b"}, headers=super_h)
    org_b = res_b.json()["id"]

    # 2. Create users
    await client.post(
        "/api/v1/auth/users",
        json={"email": "admin@org-a.uz", "password": "Password123!", "full_name": "Admin A", "role_names": ["company_admin"], "organization_id": org_a},
        headers=super_h,
    )
    await client.post(
        "/api/v1/auth/users",
        json={"email": "admin@org-b.uz", "password": "Password123!", "full_name": "Admin B", "role_names": ["company_admin"], "organization_id": org_b},
        headers=super_h,
    )

    tok_a = await get_token(client, "admin@org-a.uz", "Password123!")
    tok_b = await get_token(client, "admin@org-b.uz", "Password123!")
    head_a = {"Authorization": f"Bearer {tok_a}"}
    head_b = {"Authorization": f"Bearer {tok_b}"}

    # 3. Insert notification for Org A
    notif_a = await NotificationService.create_notification(
        test_db,
        NotificationCreate(
            organization_id=org_a,
            title="Org A Critical Storage Alert",
            message="SAN Volume 1 is 96% full.",
            severity="critical",
            category="system",
            fingerprint="san_full_a",
        ),
    )

    # 4. User A sees notification and unread count = 1
    res_list_a = await client.get("/api/v1/alerts", headers=head_a)
    assert res_list_a.status_code == 200
    assert res_list_a.json()["total"] == 1
    assert res_list_a.json()["items"][0]["id"] == notif_a.id

    res_unread_a = await client.get("/api/v1/alerts/unread-count", headers=head_a)
    assert res_unread_a.status_code == 200
    assert res_unread_a.json()["unread_count"] == 1

    # 5. User B CANNOT see Org A notification (tenant isolation)
    res_list_b = await client.get("/api/v1/alerts", headers=head_b)
    assert res_list_b.status_code == 200
    assert res_list_b.json()["total"] == 0

    res_patch_b = await client.patch(f"/api/v1/alerts/{notif_a.id}/read", headers=head_b)
    assert res_patch_b.status_code == 404  # Cannot touch Org A notification

    # 6. User A marks as read
    res_read_a = await client.patch(f"/api/v1/alerts/{notif_a.id}/read", headers=head_a)
    assert res_read_a.status_code == 200
    assert res_read_a.json()["is_read"] is True

    res_unread_after = await client.get("/api/v1/alerts/unread-count", headers=head_a)
    assert res_unread_after.json()["unread_count"] == 0

    # 7. Test mark-all-read endpoint
    await NotificationService.create_notification(
        test_db,
        NotificationCreate(
            organization_id=org_a,
            title="Org A Backup Complete",
            message="Nightly backup finished.",
            severity="info",
            category="system",
            fingerprint="backup_comp_a",
        ),
    )
    res_mark_all = await client.post("/api/v1/alerts/mark-all-read", headers=head_a)
    assert res_mark_all.status_code == 200
    assert res_mark_all.json()["updated_count"] == 1
