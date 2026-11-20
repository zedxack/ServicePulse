"""
ServicePulse - Health Endpoint Tests
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health(client: AsyncClient):
    """Test top-level health probe."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ServicePulse"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_v1_health_with_db(client: AsyncClient):
    """Test /api/v1/health probe with database verification."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_status"] == "connected"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_root_welcome(client: AsyncClient):
    """Test root endpoint provides service metadata."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ServicePulse"
    assert data["author"] == "Muhammadyusuf Usmonov"
    assert data["purpose"] == "Enterprise Hybrid RMM & ITSM Platform"
