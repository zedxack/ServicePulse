"""
ServicePulse - Users & Invitations API Test Suite
Tests:
1. Directory Listing (GET /api/v1/users & GET /api/v1/auth/users)
2. Direct User Account Provisioning (POST /api/v1/users) with immediate login verification
3. Cryptographic Invitation Issuance (POST /api/v1/invitations) with validation
4. Tenant Isolation and Role Security enforcement (Company Admin boundaries)
5. Roles listing (GET /api/v1/auth/roles)
Author: Muhammadyusuf Usmonov
"""
import pytest
from httpx import AsyncClient


async def get_token(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_users_api_authentication_and_directory_listing(client: AsyncClient):
    # 1. Unauthenticated request must be rejected with 401
    unauth_res = await client.get("/api/v1/users")
    assert unauth_res.status_code == 401

    # 2. Regular employee must be rejected with 403
    emp_token = await get_token(client, "employee@servicepulse.uz", "EmployeePass2026!")
    emp_res = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {emp_token}"})
    assert emp_res.status_code == 403

    # 3. Platform Super Admin can list all users
    super_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_headers = {"Authorization": f"Bearer {super_token}"}

    res = await client.get("/api/v1/users", headers=super_headers)
    assert res.status_code == 200
    users = res.json()
    assert isinstance(users, list)
    assert len(users) >= 1

    # Verify contract fields
    first_user = users[0]
    assert "id" in first_user
    assert "email" in first_user
    assert "full_name" in first_user
    assert "is_active" in first_user
    assert "roles" in first_user
    assert "is_primary_owner" in first_user
    assert "organization_name" in first_user

    # 4. Verify alias route /api/v1/auth/users returns identical data
    alias_res = await client.get("/api/v1/auth/users", headers=super_headers)
    assert alias_res.status_code == 200
    assert len(alias_res.json()) == len(users)


@pytest.mark.asyncio
async def test_direct_user_provisioning_and_immediate_login(client: AsyncClient):
    super_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # 1. Direct user account creation
    new_user_payload = {
        "email": "direct.provisioned@example.com",
        "full_name": "Direct Provisioned Admin",
        "password": "SecureDirectPassword2026!",
        "role_name": "it_admin",
        "organization_id": 1,
        "is_active": True,
    }

    create_res = await client.post("/api/v1/users", json=new_user_payload, headers=super_headers)
    assert create_res.status_code == 201, f"Failed: {create_res.text}"
    user_data = create_res.json()

    assert user_data["email"] == "direct.provisioned@example.com"
    assert user_data["full_name"] == "Direct Provisioned Admin"
    assert user_data["is_active"] is True
    assert any(r["name"] == "it_admin" for r in user_data["roles"])

    # 2. Verify user can immediately sign in at /api/v1/auth/login with the provisioned credentials
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "direct.provisioned@example.com", "password": "SecureDirectPassword2026!"},
    )
    assert login_res.status_code == 200, f"Immediate login failed: {login_res.text}"
    login_data = login_res.json()

    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["primary_dashboard"] == "sysadmin"
    assert "it_admin" in login_data["roles"]


@pytest.mark.asyncio
async def test_invitation_issuance_and_validation(client: AsyncClient):
    super_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # 1. Issue an invitation token
    invite_payload = {
        "role_name": "support",
        "organization_id": 1,
        "invited_email": "invited.technician@example.com",
        "max_uses": 1,
        "expires_in_days": 7,
    }

    invite_res = await client.post("/api/v1/invitations", json=invite_payload, headers=super_headers)
    assert invite_res.status_code == 201, f"Failed: {invite_res.text}"
    invite_data = invite_res.json()

    assert "raw_token" in invite_data
    assert "invitation" in invite_data
    raw_token = invite_data["raw_token"]
    assert raw_token.startswith("sp_inv_")

    # 2. Validate the invitation token via public validation endpoint
    validate_res = await client.post(
        "/api/v1/invitations/validate",
        json={"invitation_code": raw_token},
    )
    assert validate_res.status_code == 200, f"Validation failed: {validate_res.text}"
    val_data = validate_res.json()

    assert val_data["valid"] is True
    assert val_data["role_name"] == "support"
    assert val_data["organization_name"] == "Example Corporation"

    # 3. List invitations at GET /api/v1/invitations
    list_res = await client.get("/api/v1/invitations", headers=super_headers)
    assert list_res.status_code == 200
    invitations = list_res.json()
    assert any(raw_token.startswith(inv["token_prefix"]) for inv in invitations)


@pytest.mark.asyncio
async def test_company_admin_tenant_isolation_and_role_guards(client: AsyncClient):
    comp_token = await get_token(client, "company_admin@servicepulse.uz", "CompanyAdminPass2026!")
    comp_headers = {"Authorization": f"Bearer {comp_token}"}

    # 1. Company admin can list users (filtered to their tenant)
    comp_users_res = await client.get("/api/v1/users", headers=comp_headers)
    assert comp_users_res.status_code == 200
    for u in comp_users_res.json():
        assert u["organization_id"] == 1

    # 2. Company admin cannot provision a user with platform_super_admin role
    forbidden_role_payload = {
        "email": "illegal.super@example.com",
        "full_name": "Illegal Super Admin",
        "password": "Password123!",
        "role_name": "platform_super_admin",
        "organization_id": 1,
    }
    forbidden_res = await client.post("/api/v1/users", json=forbidden_role_payload, headers=comp_headers)
    assert forbidden_res.status_code == 403

    # 3. Company admin cannot provision a user for another organization
    cross_org_payload = {
        "email": "cross.org@example.com",
        "full_name": "Cross Org User",
        "password": "Password123!",
        "role_name": "employee",
        "organization_id": 9999,
    }
    cross_res = await client.post("/api/v1/users", json=cross_org_payload, headers=comp_headers)
    assert cross_res.status_code == 403


@pytest.mark.asyncio
async def test_roles_listing_endpoint(client: AsyncClient):
    # Any authenticated administrative user or client can list roles
    super_token = await get_token(client, "admin@servicepulse.uz", "AdminPass2026!")
    res = await client.get("/api/v1/auth/roles", headers={"Authorization": f"Bearer {super_token}"})
    assert res.status_code == 200
    roles = res.json()
    assert isinstance(roles, list)
    role_names = [r["name"] for r in roles]
    assert "platform_super_admin" in role_names
    assert "company_admin" in role_names
    assert "it_admin" in role_names
    assert "support" in role_names
    assert "executive" in role_names
    assert "employee" in role_names
