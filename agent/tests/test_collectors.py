"""
ServicePulse Windows Agent - Collectors Test Suite
Verifies genuine host telemetry gathering and simulated edge case parsing.
Author: Muhammadyusuf Usmonov
"""
import json
import subprocess
from unittest.mock import MagicMock, patch

from servicepulse.collectors import (
    DefenderCollector,
    NetworkCollector,
    SystemCollector,
    WindowsActivationCollector,
)


def test_system_collector_cpu():
    """Verify CPU telemetry gathers non-negative utilization and logical core counts."""
    cpu = SystemCollector.collect_cpu()
    assert 0.0 <= cpu.cpu_percent <= 100.0
    assert cpu.core_count_logical >= 1


def test_system_collector_ram():
    """Verify RAM telemetry gathers valid memory figures in Megabytes."""
    ram = SystemCollector.collect_ram()
    assert 0.0 <= ram.ram_percent <= 100.0
    assert ram.ram_total_mb > 0.0
    assert ram.ram_used_mb >= 0.0
    assert ram.ram_available_mb >= 0.0
    assert ram.ram_used_mb <= ram.ram_total_mb + 100.0  # margin for dynamic allocation


def test_system_collector_disk():
    """Verify fixed disk metrics gather valid capacities and ignore removable media."""
    disk = SystemCollector.collect_disk()
    assert 0.0 <= disk.disk_percent <= 100.0
    assert disk.disk_total_gb > 0.0
    assert disk.disk_used_gb >= 0.0
    assert len(disk.drives) >= 1
    # Check primary mount
    primary = disk.drives[0]
    assert "mountpoint" in primary
    assert primary["total_gb"] > 0.0


def test_system_collector_os():
    """Verify operating system metrics include hostname, version, and uptime."""
    os_info = SystemCollector.collect_os()
    assert os_info.hostname != ""
    assert os_info.os_name != ""
    assert os_info.uptime_seconds >= 0.0


def test_system_collector_collect_all():
    """Verify consolidated telemetry structure gathers all subsystems."""
    metrics = SystemCollector.collect_all()
    assert metrics.cpu.core_count_logical >= 1
    assert metrics.ram.ram_total_mb > 0.0
    assert metrics.disk.disk_total_gb > 0.0
    assert metrics.os.hostname != ""


def test_network_collector():
    """Verify network collector returns primary IP and interface list."""
    net = NetworkCollector.collect()
    assert net.primary_ip != ""
    assert net.hostname != ""
    assert isinstance(net.interfaces, list)


def test_windows_activation_live_or_fallback():
    """Verify Windows activation returns a valid typed status structure."""
    act = WindowsActivationCollector.collect(timeout_seconds=5)
    assert act.status in ("licensed", "not_activated", "in_grace_period", "notification", "unavailable")
    # Verify product key is never full key (5 alphanumeric partial max)
    if act.partial_key:
        assert len(act.partial_key) <= 5


@patch("subprocess.run")
def test_windows_activation_status_parsing(mock_run):
    """Verify activation parser correctly categorizes SLAPI LicenseStatus codes."""
    # Case 1: Licensed (1)
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "Name": "Windows(R), Professional edition",
            "Description": "Windows Operating System, OEM channel",
            "LicenseStatus": 1,
            "PartialProductKey": "ABC12"
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        act = WindowsActivationCollector.collect()
        assert act.status == "licensed"
        assert act.is_genuine is True
        assert act.partial_key == "ABC12"

    # Case 2: Grace period (2)
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "Name": "Windows(R), Enterprise edition",
            "Description": "VOLUME_KMS channel",
            "LicenseStatus": 2,
            "PartialProductKey": "XYZ89"
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        act = WindowsActivationCollector.collect()
        assert act.status == "in_grace_period"
        assert act.is_genuine is False

    # Case 3: Not activated (0)
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({"Name": "Windows", "LicenseStatus": 0}),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        act = WindowsActivationCollector.collect()
        assert act.status == "not_activated"
        assert act.is_genuine is False


@patch("subprocess.run")
def test_windows_activation_timeout_and_error_handling(mock_run):
    """Verify activation returns unavailable on timeout or non-zero error without crashing."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=5)
    with patch("sys.platform", "win32"):
        act = WindowsActivationCollector.collect()
        assert act.status == "unavailable"
        assert "timed out" in (act.details or "")


def test_defender_collector_live_or_fallback():
    """Verify Defender collector returns typed status on host."""
    def_stat = DefenderCollector.collect(timeout_seconds=5)
    assert def_stat.status in ("healthy", "realtime_disabled", "antivirus_disabled", "signatures_outdated", "unavailable")


@patch("subprocess.run")
def test_defender_status_evaluations(mock_run):
    """Verify Defender statuses: healthy, realtime_disabled, antivirus_disabled, signatures_outdated."""
    # Case 1: Healthy
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "AntivirusEnabled": True,
            "RealTimeProtectionEnabled": True,
            "AntispywareEnabled": True,
            "AntivirusSignatureAge": 1
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        stat = DefenderCollector.collect()
        assert stat.status == "healthy"
        assert stat.antivirus_enabled is True
        assert stat.realtime_protection_enabled is True

    # Case 2: Realtime disabled
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "AntivirusEnabled": True,
            "RealTimeProtectionEnabled": False,
            "AntispywareEnabled": True,
            "AntivirusSignatureAge": 0
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        stat = DefenderCollector.collect()
        assert stat.status == "realtime_disabled"

    # Case 3: Antivirus disabled
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "AntivirusEnabled": False,
            "RealTimeProtectionEnabled": False,
            "AntispywareEnabled": False,
            "AntivirusSignatureAge": 0
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        stat = DefenderCollector.collect()
        assert stat.status == "antivirus_disabled"

    # Case 4: Signatures outdated
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "AntivirusEnabled": True,
            "RealTimeProtectionEnabled": True,
            "AntispywareEnabled": True,
            "AntivirusSignatureAge": 21
        }),
        stderr=""
    )
    with patch("sys.platform", "win32"):
        stat = DefenderCollector.collect()
        assert stat.status == "signatures_outdated"
