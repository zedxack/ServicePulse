"""
ServicePulse Windows Agent - Security & Hardening Test Suite
Verifies strict shell injection rejection, allowlist enforcement, and credential redaction.
Author: Muhammadyusuf Usmonov
"""
import logging
from unittest.mock import MagicMock

import pytest
from servicepulse.commands import CommandAllowlist, CommandDispatcher
from servicepulse.commands.schemas import parse_and_validate_command_parameters
from servicepulse.logging.setup import SensitiveFilter


def test_reject_unknown_actions():
    """Verify arbitrary action names outside the local allowlist are rejected."""
    disallowed = [
        "download_and_execute",
        "format_disk",
        "exec_powershell",
        "bash",
        "cmd",
        "add_user",
        "disable_firewall",
    ]
    for action in disallowed:
        assert CommandAllowlist.is_action_allowed(action) is False
        with pytest.raises(ValueError, match="not permitted by local security policy"):
            parse_and_validate_command_parameters(action, "{}")


def test_reject_prohibited_system_services():
    """Verify critical Windows OS system services can never be targeted for restarts."""
    critical_services = ["lsass", "csrss", "smss", "winlogon", "services", "system"]
    for svc in critical_services:
        assert CommandAllowlist.is_service_allowed(svc) is False
        with pytest.raises(ValueError, match="not in the allowed remediation services list"):
            parse_and_validate_command_parameters("restart_service", f'{{"service_name": "{svc}"}}')


def test_reject_shell_metacharacters_in_service_name():
    """Verify service names with shell injection characters are strictly rejected."""
    injection_attempts = [
        "spooler; rm -rf C:\\",
        "wuauserv & calc.exe",
        "spooler | whoami",
        "wuauserv`calc`",
        "spooler\nnotepad",
    ]
    for bad_name in injection_attempts:
        with pytest.raises(ValueError):
            parse_and_validate_command_parameters("restart_service", f'{{"service_name": "{bad_name}"}}')


def test_reject_unapproved_software_titles():
    """Verify software catalog prevents installation of unapproved arbitrary packages."""
    unapproved = ["CryptoMiner", "Keylogger", "UnknownApp.exe", "MalwarePack"]
    for app in unapproved:
        assert CommandAllowlist.is_software_approved(app) is False
        with pytest.raises(ValueError, match="not in the approved software catalog"):
            parse_and_validate_command_parameters("install_approved_software", f'{{"software": "{app}"}}')


def test_reject_shell_injection_in_software_version():
    """Verify software versions containing shell metacharacters are rejected."""
    bad_versions = [
        "1.0.0; powershell -c calc.exe",
        "2.0 && net user hacker /add",
        "1.0`whoami`",
    ]
    for bv in bad_versions:
        with pytest.raises(ValueError, match="illegal characters or shell metacharacters"):
            parse_and_validate_command_parameters(
                "install_approved_software",
                f'{{"software": "7-Zip", "version": "{bv}"}}'
            )


def test_dispatcher_reports_failure_for_invalid_command():
    """Verify dispatcher safely reports failed status to backend if command fails validation."""
    mock_client = MagicMock()
    mock_client.get_pending_commands.return_value = [
        {
            "id": 999,
            "action_name": "malicious_action",
            "parameters": '{"payload": "hack"}',
        }
    ]

    dispatcher = CommandDispatcher(mock_client)
    dispatcher.poll_and_process_commands()

    # Verify acknowledged and then reported as failed
    mock_client.acknowledge_command.assert_called_once_with(999)
    mock_client.report_command_result.assert_called_once()
    args = mock_client.report_command_result.call_args[1]
    assert args["command_id"] == 999
    assert args["status"] == "failed"
    assert "validation failed" in args["execution_result"]


def test_sensitive_log_filter_redaction():
    """Verify sensitive tokens and secrets are redacted from log messages."""
    filt = SensitiveFilter()

    # 1. Agent token
    rec1 = logging.LogRecord("test", logging.INFO, "test.py", 10, "Using token: sp_tok_super_secret_agent_key_12345", None, None)
    filt.filter(rec1)
    assert "sp_tok_super_secret" not in rec1.msg
    assert "[REDACTED_TOKEN]" in rec1.msg

    # 2. Authorization header
    rec2 = logging.LogRecord("test", logging.INFO, "test.py", 10, "Headers: Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc", None, None)
    filt.filter(rec2)
    assert "[REDACTED_BEARER]" in rec2.msg

    # 3. Product key
    rec3 = logging.LogRecord("test", logging.INFO, "test.py", 10, "Activation key: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX", None, None)
    filt.filter(rec3)
    assert "[REDACTED_PRODUCT_KEY]" in rec3.msg
