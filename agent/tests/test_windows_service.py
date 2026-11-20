"""
ServicePulse Windows Agent - Windows Service Component Test Suite
Verifies service attributes, SCM lifecycle queries, and graceful termination.
Author: Muhammadyusuf Usmonov
"""
from servicepulse.service.installer import ServiceManager
from servicepulse.service.windows_service import ServicePulseWindowsService


def test_service_metadata_and_constants():
    """Verify service names and display configuration adhere to Windows SCM standards."""
    assert ServicePulseWindowsService._svc_name_ == "ServicePulseAgent"
    assert "ServicePulse" in ServicePulseWindowsService._svc_display_name_


def test_service_status_query():
    """Verify ServiceManager queries service state without raising uncaught exceptions."""
    status = ServiceManager.get_service_status()
    assert "installed" in status
    assert "status" in status
    assert status["status"] in ("running", "stopped", "not_installed", "unavailable", "error", "unknown")
