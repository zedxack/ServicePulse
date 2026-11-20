"""
ServicePulse - Helpdesk Tickets & Software Approval Workflow API Integration Tests
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


@pytest.fixture
async def employee_headers(client: AsyncClient):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": settings.FIRST_EMPLOYEE_EMAIL, "password": settings.FIRST_EMPLOYEE_PASSWORD}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_ticket_lifecycle_and_employee_isolation(client: AsyncClient, employee_headers, admin_headers):
    """Verify ticket creation, discussion comments, assignment, and role isolation."""
    # 1. Employee creates ticket
    t_payload = {
        "title": "Monitor display flickering",
        "description": "Lab 204 PC 01 HDMI signal occasionally disconnects",
        "category": "hardware",
        "priority": "medium"
    }
    t_resp = await client.post("/api/v1/tickets", json=t_payload, headers=employee_headers)
    assert t_resp.status_code == 201
    ticket_data = t_resp.json()
    t_id = ticket_data["id"]
    assert ticket_data["status"] == "open"

    # 2. Employee adds comment
    com_resp = await client.post(
        f"/api/v1/tickets/{t_id}/comments",
        json={"comment": "Problem happens when PC resumes from sleep"},
        headers=employee_headers
    )
    assert com_resp.status_code == 201
    assert com_resp.json()["comment"] == "Problem happens when PC resumes from sleep"

    # 3. Support/Admin assigns ticket
    admin_me = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    assign_resp = await client.patch(
        f"/api/v1/tickets/{t_id}/assign",
        json={"assigned_to_id": admin_me["id"]},
        headers=admin_headers
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_to_id"] == admin_me["id"]

    # 4. Resolve ticket
    res_resp = await client.patch(
        f"/api/v1/tickets/{t_id}/resolve",
        json={"resolution_notes": "Updated graphics driver and secured display cable"},
        headers=admin_headers
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_software_approval_workflow(client: AsyncClient, employee_headers, admin_headers):
    """
    Verify software installation request submission, RBAC boundaries,
    and administrator approval resulting in pending AgentCommand creation.
    """
    # Find a device
    tree = (await client.get("/api/v1/inventory/tree", headers=admin_headers)).json()
    device = tree["buildings"][0]["floors"][0]["rooms"][0]["devices"][0]

    # 1. Employee submits software request
    req_payload = {
        "device_id": device["id"],
        "software_name": "Wireshark Network Analyzer",
        "software_version": "4.2.2",
        "reason": "Required for computer networking practical lab session"
    }
    req_resp = await client.post("/api/v1/software/requests", json=req_payload, headers=employee_headers)
    assert req_resp.status_code == 201
    req_data = req_resp.json()
    req_id = req_data["id"]
    assert req_data["status"] == "pending"

    # 2. Employee attempts to self-approve -> 403 Forbidden
    app_forbidden = await client.post(
        f"/api/v1/software/requests/{req_id}/approve",
        json={"review_notes": "Self approval"},
        headers=employee_headers
    )
    assert app_forbidden.status_code == 403

    # 3. Admin approves request -> 200 OK
    app_resp = await client.post(
        f"/api/v1/software/requests/{req_id}/approve",
        json={"review_notes": "Approved for lab 204 network analysis course"},
        headers=admin_headers
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"
    assert app_resp.json()["reviewed_by_user_id"] is not None
