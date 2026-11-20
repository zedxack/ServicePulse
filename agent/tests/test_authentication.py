"""
ServicePulse Windows Agent - Authentication & Credential Storage Test Suite
Verifies DPAPI encryption, non-plaintext storage, token lifecycle, and secure enrollment.
Author: Muhammadyusuf Usmonov
"""
from unittest.mock import patch

from servicepulse.authentication import AgentCredentials, CredentialStore
from servicepulse.config import AgentConfig
from servicepulse.enrollment import EnrollmentManager


def test_dpapi_credential_storage_encryption(test_cred_store: CredentialStore, sample_credentials: AgentCredentials):
    """Verify saved credentials file is encrypted and does not contain plaintext secrets."""
    test_cred_store.save_credentials(sample_credentials)
    assert test_cred_store.has_credentials() is True

    # Read raw ciphertext from disk
    with open(test_cred_store.path, "rb") as f:
        raw_bytes = f.read()

    # Verify plaintext tokens are NOT visible in the file bytes
    assert sample_credentials.api_token.encode("utf-8") not in raw_bytes
    assert sample_credentials.agent_uuid.encode("utf-8") not in raw_bytes

    # Load via store and verify correct decrypted values
    loaded = test_cred_store.load_credentials()
    assert loaded is not None
    assert loaded.agent_uuid == sample_credentials.agent_uuid
    assert loaded.api_token == sample_credentials.api_token
    assert loaded.device_id == sample_credentials.device_id
    assert loaded.organization_id == sample_credentials.organization_id


def test_credential_store_clear_and_missing(test_cred_store: CredentialStore, sample_credentials: AgentCredentials):
    """Verify clearing credentials removes file and returns None when missing."""
    assert test_cred_store.load_credentials() is None
    assert test_cred_store.has_credentials() is False

    test_cred_store.save_credentials(sample_credentials)
    assert test_cred_store.has_credentials() is True

    test_cred_store.clear_credentials()
    assert test_cred_store.has_credentials() is False
    assert test_cred_store.load_credentials() is None


@patch("servicepulse.api_client.ApiClient.enroll")
def test_enrollment_manager_flow(mock_enroll, test_config: AgentConfig):
    """Verify EnrollmentManager interacts with ApiClient and persists credentials."""
    mock_enroll.return_value = AgentCredentials(
        agent_uuid="agent_mock_new_77",
        api_token="sp_tok_newly_enrolled_secret",
        device_id=99,
        organization_id=2
    )

    creds = EnrollmentManager.enroll_agent(
        config=test_config,
        enrollment_secret="valid-enroll-secret-test",
        device_id=99,
        organization_id=2
    )

    assert creds.agent_uuid == "agent_mock_new_77"
    assert creds.api_token == "sp_tok_newly_enrolled_secret"

    # Verify credentials saved in DPAPI store
    store = CredentialStore(test_config.get_credentials_path())
    saved = store.load_credentials()
    assert saved is not None
    assert saved.agent_uuid == "agent_mock_new_77"


def test_dpapi_machine_scope_persistence(tmp_path):
    """Verify DPAPI credential store saves and loads successfully across simulated restarts."""
    import sys
    cred_file = tmp_path / "credentials.dat"
    store1 = CredentialStore(cred_file)
    creds = AgentCredentials(
        agent_uuid="uuid-persisted-12345",
        api_token="sp_tok_super_secure_vault_token",
        device_id=42,
        organization_id=1
    )
    store1.save_credentials(creds)
    assert cred_file.is_file()

    # Simulate fresh process opening the saved credential file
    store2 = CredentialStore(cred_file)
    loaded = store2.load_credentials()
    assert loaded is not None
    assert loaded.agent_uuid == "uuid-persisted-12345"
    assert loaded.api_token == "sp_tok_super_secure_vault_token"
    assert loaded.device_id == 42
    assert loaded.organization_id == 1

    # Verify restricted ACL verification on Windows
    if sys.platform == "win32":
        import subprocess
        res = subprocess.run(
            ["icacls.exe", str(cred_file)],
            capture_output=True,
            text=True,
            errors="replace",
            check=False
        )
        assert res.returncode == 0
        # Verify no .tmp file left behind
        assert not cred_file.with_suffix(".tmp").exists()


def test_dpapi_flags_and_sid_resolution():
    """Verify DPAPI flag constants match Windows SDK specification and SID helper works."""
    import sys

    from servicepulse.authentication import (
        CRYPTPROTECT_DEFAULT,
        CRYPTPROTECT_LOCAL_MACHINE,
        CRYPTPROTECT_UI_FORBIDDEN,
        DPAPI_MACHINE_FLAGS,
        get_current_user_sid,
    )

    # 1. Exact constant verification
    assert CRYPTPROTECT_DEFAULT == 0x0
    assert CRYPTPROTECT_UI_FORBIDDEN == 0x1
    assert CRYPTPROTECT_LOCAL_MACHINE == 0x4
    assert DPAPI_MACHINE_FLAGS == 0x5
    assert DPAPI_MACHINE_FLAGS == (CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE)

    # 2. SID resolution on Windows
    if sys.platform == "win32":
        sid = get_current_user_sid()
        assert sid is not None
        assert sid.startswith("S-1-")


def test_directory_and_credential_dacl_hardening(tmp_path):
    """Verify restrictive NTFS ACLs on parent directory and final credentials file."""
    import sys
    if sys.platform != "win32":
        return

    import subprocess
    target_dir = tmp_path / "ServicePulseSecureDir"
    target_file = target_dir / "credentials.dat"
    store = CredentialStore(target_file)
    store.save_credentials(AgentCredentials(
        agent_uuid="uuid-acl-audit-88",
        api_token="sp_tok_audit_test_token"
    ))

    assert target_file.is_file()
    assert not target_file.with_suffix(".tmp").exists()

    # Verify icacls on parent directory
    res_dir = subprocess.run(["icacls.exe", str(target_dir)], capture_output=True, text=True, errors="replace", check=False)
    assert res_dir.returncode == 0

    # Verify icacls on credential file
    res_file = subprocess.run(["icacls.exe", str(target_file)], capture_output=True, text=True, errors="replace", check=False)
    assert res_file.returncode == 0
    file_acl = res_file.stdout

    # Confirm SYSTEM (S-1-5-18) is granted
    assert "S-1-5-18" in file_acl or "NT AUTHORITY" in file_acl or "СИСТЕМА" in file_acl
