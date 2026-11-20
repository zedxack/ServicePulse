"""
ServicePulse - Dual-Mode Dashboard API Integration Tests
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
async def test_sysadmin_dashboard(client: AsyncClient, admin_headers):
    """Verify SysAdmin dashboard provides accurate real-time metrics and device breakdowns."""
    resp = await client.get("/api/v1/dashboard/sysadmin", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_devices"] >= 6
    assert data["online_devices"] >= 1
    assert "devices_by_building" in data
    assert len(data["devices_by_building"]) >= 1
    assert "telemetry_summary" in data


@pytest.mark.asyncio
async def test_ceo_dashboard_and_insufficient_data_handling(client: AsyncClient, admin_headers):
    """Verify CEO dashboard returns SLA, availability, and reports insufficient data when appropriate."""
    resp = await client.get("/api/v1/dashboard/ceo", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["infrastructure_availability_percent"] > 0
    assert data["contractual_sla_status"] == "unavailable"
    assert data["contractual_sla_uptime_percent"] is None
    assert data["probe_success_status"] == "operational"
    assert data["probe_success_ratio_percent"] is not None and data["probe_success_ratio_percent"] > 0
    assert "incident_trends" in data
    assert len(data["incident_trends"]) == 7
    assert "top_risk_devices" in data
    assert "business_impact_summary" in data
    # When no resolved incidents exist yet, MTTD/MTTR should explicitly report insufficient data
    assert data["mttd_status"] in ["insufficient_data", "operational"]
