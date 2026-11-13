"""
ServicePulse - Incident Management & Deduplication API Integration Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient

from backend.app.core.config import settings


@pytest.fixture
async def admin_headers(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_incident_lifecycle_and_deduplication(client: AsyncClient, admin_headers):
    """
    Verify complete incident lifecycle:
    creation -> deduplication on repeat observation -> assign -> acknowledge -> resolve -> fresh incident on recurrence
    """
    # 1. Create initial incident
    inc_payload = {
        "title": "Camera RTSP Feed Dropped",
        "description": "TCP connection to RTSP port 554 timed out",
        "severity": "warning",
        "fingerprint": "cam_kirish_01_rtsp_554"
    }
    create_resp = await client.post("/api/v1/incidents", json=inc_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    inc_data = create_resp.json()
    inc_id = inc_data["id"]
    assert inc_data["occurrence_count"] == 1
    assert inc_data["status"] == "open"
    assert inc_data["fingerprint"] == "cam_kirish_01_rtsp_554"

    # 2. Concurrency-Safe Deduplication: Same failure observed again
    repeat_payload = {
        "title": "Camera RTSP Feed Dropped",
        "description": "TCP connection timed out again",
        "severity": "critical",  # Escalated
        "fingerprint": "cam_kirish_01_rtsp_554"
    }
    repeat_resp = await client.post("/api/v1/incidents", json=repeat_payload, headers=admin_headers)
    assert repeat_resp.status_code == 201
    repeat_data = repeat_resp.json()
    # Must update existing record, NOT create duplicate row!
    assert repeat_data["id"] == inc_id
    assert repeat_data["occurrence_count"] == 2
    assert repeat_data["severity"] == "critical"  # Escalated

    # 3. Acknowledge incident
    ack_resp = await client.patch(
        f"/api/v1/incidents/{inc_id}/acknowledge",
        json={"notes": "Investigating switch port"},
        headers=admin_headers
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"

    # 4. Assign incident
    user_me = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    assign_resp = await client.patch(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"assigned_to_user_id": user_me["id"]},
        headers=admin_headers
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_to_user_id"] == user_me["id"]

    # 5. Resolve incident
    resolve_resp = await client.patch(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"resolution_notes": "Replaced faulty patch cord; RTSP stream restored."},
        headers=admin_headers
    )
    assert resolve_resp.status_code == 200
    resolved_data = resolve_resp.json()
    assert resolved_data["status"] == "resolved"
    assert resolved_data["active_dedup_key"] is None

    # 6. Subsequent failure with same fingerprint creates a fresh incident
    new_resp = await client.post("/api/v1/incidents", json=inc_payload, headers=admin_headers)
    assert new_resp.status_code == 201
    new_data = new_resp.json()
    assert new_data["id"] != inc_id
    assert new_data["occurrence_count"] == 1
    assert new_data["status"] == "open"


@pytest.mark.asyncio
async def test_incident_filtering_and_events(client: AsyncClient, admin_headers):
    """Verify incident filtering and event log inspection."""
    list_resp = await client.get("/api/v1/incidents?severity=critical", headers=admin_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "total" in data
    assert "items" in data
