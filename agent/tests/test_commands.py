"""
ServicePulse Windows Agent - Command Processing Test Suite
Verifies action validation, safe execution, post-execution verification, and dispatcher orchestration.
Author: Muhammadyusuf Usmonov
"""
from unittest.mock import MagicMock

from servicepulse.commands import (
    CommandDispatcher,
    CommandExecutor,
    DiagnosticCheckParams,
    InstallApprovedSoftwareParams,
    NotifyAdminParams,
    RecheckNetworkParams,
    RestartAgentParams,
    RestartServiceParams,
)
from servicepulse.commands.schemas import parse_and_validate_command_parameters
from servicepulse.commands.verification import CommandVerifier


def test_command_parameter_parsing_valid_actions():
    """Verify all allowlisted action parameters parse into validated Pydantic models."""
    # 1. restart_service
    p1 = parse_and_validate_command_parameters("restart_service", '{"service_name": "spooler"}')
    assert isinstance(p1, RestartServiceParams)
    assert p1.service_name == "spooler"

    # 2. restart_servicepulse_agent
    p2 = parse_and_validate_command_parameters("restart_servicepulse_agent", '{"reason": "upgrade"}')
    assert isinstance(p2, RestartAgentParams)
    assert p2.reason == "upgrade"

    # 3. run_diagnostic_check
    p3 = parse_and_validate_command_parameters("run_diagnostic_check", '{"check_type": "ping", "target": "127.0.0.1"}')
    assert isinstance(p3, DiagnosticCheckParams)
    assert p3.check_type == "ping"

    # 4. recheck_network_endpoint
    p4 = parse_and_validate_command_parameters("recheck_network_endpoint", '{"target": "192.168.1.1", "protocol": "tcp", "port": 80}')
    assert isinstance(p4, RecheckNetworkParams)
    assert p4.target == "192.168.1.1"

    # 5. notify_administrator
    p5 = parse_and_validate_command_parameters("notify_administrator", '{"message": "High memory", "severity": "warning"}')
    assert isinstance(p5, NotifyAdminParams)
    assert p5.severity == "warning"

    # 6. install_approved_software
    p6 = parse_and_validate_command_parameters("install_approved_software", '{"software": "7-Zip", "version": "24.08"}')
    assert isinstance(p6, InstallApprovedSoftwareParams)
    assert p6.software == "7-Zip"


def test_command_execution_simulation_modes():
    """Verify CommandExecutor handles all actions safely in simulation mode."""
    # Service restart simulation
    res1 = CommandExecutor.execute_restart_service(RestartServiceParams(service_name="spooler"), simulation=True)
    assert res1.success is True
    assert res1.status == "succeeded"
    assert "SIMULATION" in res1.output

    # Diagnostic simulation
    res2 = CommandExecutor.execute_diagnostic_check(DiagnosticCheckParams(check_type="dns", target="localhost"), simulation=True)
    assert res2.success is True

    # Network recheck simulation
    res3 = CommandExecutor.execute_recheck_network(RecheckNetworkParams(target="10.0.0.1"), simulation=True)
    assert res3.success is True

    # Notification
    res4 = CommandExecutor.execute_notify_admin(NotifyAdminParams(message="Test alert", severity="info"))
    assert res4.success is True

    # Software install simulation
    res5 = CommandExecutor.execute_install_approved_software(InstallApprovedSoftwareParams(software="Git"), simulation=True)
    assert res5.success is True


def test_command_verification():
    """Verify CommandVerifier checks service state."""
    params = RestartServiceParams(service_name="spooler")
    verified, msg = CommandVerifier.verify_service_running(params, simulation=True)
    assert verified is True
    assert "verified in RUNNING state" in msg


def test_command_dispatcher_end_to_end():
    """Verify CommandDispatcher polls, acknowledges, validates, executes, and reports result."""
    mock_client = MagicMock()
    mock_client.get_pending_commands.return_value = [
        {
            "id": 101,
            "action_name": "restart_service",
            "parameters": '{"service_name": "spooler"}',
            "is_simulation": True,
        }
    ]

    dispatcher = CommandDispatcher(mock_client, simulation_mode=True)
    processed = dispatcher.poll_and_process_commands()

    assert processed == 1
    mock_client.acknowledge_command.assert_called_once_with(101)
    mock_client.report_command_result.assert_called_once()
    call_args = mock_client.report_command_result.call_args[1]
    assert call_args["command_id"] == 101
    assert call_args["status"] == "succeeded"
    assert "SIMULATION" in call_args["execution_result"]


def test_command_expiration():
    """Verify stale commands older than max_command_age_seconds are rejected as expired."""
    import datetime
    mock_client = MagicMock()
    stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).isoformat()
    mock_client.get_pending_commands.return_value = [
        {
            "id": 202,
            "action_name": "restart_service",
            "parameters": '{"service_name": "spooler"}',
            "created_at": stale_time,
            "is_simulation": True,
        }
    ]

    dispatcher = CommandDispatcher(mock_client, simulation_mode=True, max_command_age_seconds=3600)
    processed = dispatcher.poll_and_process_commands()

    assert processed == 1
    mock_client.acknowledge_command.assert_called_once_with(202)
    mock_client.report_command_result.assert_called_once()
    call_args = mock_client.report_command_result.call_args[1]
    assert call_args["command_id"] == 202
    assert call_args["status"] == "failed"
    assert "expired" in call_args["execution_result"].lower()


def test_command_deduplication():
    """Verify duplicate command dispatches are ignored by the dispatcher cache."""
    mock_client = MagicMock()
    cmd = {
        "id": 303,
        "action_name": "restart_service",
        "parameters": '{"service_name": "spooler"}',
        "is_simulation": True,
    }
    mock_client.get_pending_commands.return_value = [cmd]

    dispatcher = CommandDispatcher(mock_client, simulation_mode=True)
    # First dispatch
    processed1 = dispatcher.poll_and_process_commands()
    assert processed1 == 1
    assert mock_client.report_command_result.call_count == 1

    # Second poll with same command ID
    processed2 = dispatcher.poll_and_process_commands()
    assert processed2 == 1
    # report_command_result should still only be called once because duplicate was skipped
    assert mock_client.report_command_result.call_count == 1


def test_install_approved_software_hash_and_url_validation():
    """Verify hash format and HTTPS requirements for software installation parameters."""
    import pytest

    # Valid SHA256 and HTTPS download_url
    valid_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    p = parse_and_validate_command_parameters(
        "install_approved_software",
        {
            "software": "Wireshark",
            "version": "4.2.0",
            "sha256": valid_sha256,
            "download_url": "https://127.0.0.1/packages/wireshark.msi"
        }
    )
    assert isinstance(p, InstallApprovedSoftwareParams)
    assert p.sha256 == valid_sha256
    assert p.download_url == "https://127.0.0.1/packages/wireshark.msi"

    # Invalid SHA256 length / characters rejected
    with pytest.raises(ValueError, match="Cryptographic sha256 checksum"):
        parse_and_validate_command_parameters(
            "install_approved_software",
            {"software": "Git", "sha256": "invalid_not_hex_or_short"}
        )

    # Insecure HTTP download_url rejected
    with pytest.raises(ValueError, match="Download URL must use secure HTTPS protocol"):
        parse_and_validate_command_parameters(
            "install_approved_software",
            {"software": "Git", "download_url": "http://insecure-site.com/git.exe"}
        )


def test_file_hash_and_authenticode_verification(tmp_path):
    """Verify cryptographic file hash verification and authenticode signature routine."""
    import hashlib
    test_file = tmp_path / "sample_binary.exe"
    data = b"Enterprise Signed Application Payload 2026"
    test_file.write_bytes(data)
    expected_hash = hashlib.sha256(data).hexdigest()

    # Hash verification
    assert CommandExecutor.verify_file_sha256(test_file, expected_hash) is True
    assert CommandExecutor.verify_file_sha256(test_file, "0000000000000000000000000000000000000000000000000000000000000000") is False

    # Authenticode check on unsigned test file returns not trusted
    is_valid, msg = CommandExecutor.verify_authenticode_signature(test_file)
    assert is_valid is False
    assert "not trusted" in msg.lower() or "error" in msg.lower()
