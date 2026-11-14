"""
ServicePulse Native Windows Agent - Windows Service Controller Implementation
Integrates the agent as a native background Windows Service managed via SCM (services.msc).
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import sys
import threading
from typing import Optional

from servicepulse.agent import ServicePulseAgent
from servicepulse.logging.setup import get_logger, setup_logging

logger = get_logger()

# Import win32 service modules if on Windows
_HAS_WIN32SERVICE = False
if sys.platform == "win32":
    try:
        import servicemanager
        import win32event
        import win32service
        import win32serviceutil
        _HAS_WIN32SERVICE = True
    except ImportError:
        _HAS_WIN32SERVICE = False


if _HAS_WIN32SERVICE:
    class ServicePulseWindowsService(win32serviceutil.ServiceFramework):
        """Native Windows Service wrapper for ServicePulse Agent."""

        _svc_name_ = "ServicePulseAgent"
        _svc_display_name_ = "ServicePulse Monitoring Agent"
        _svc_description_ = (
            "ServicePulse Native Windows Monitoring and Automated Remediation Agent. "
            "Continuously monitors endpoint health, reports telemetry, and processes authorized remediation."
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self._stop_event = threading.Event()
            self._agent_thread: Optional[threading.Thread] = None

        def SvcStop(self):
            """Invoked by Windows SCM when service stop is requested."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            logger.info("Windows Service stop requested by SCM.")
            self._stop_event.set()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            """Main execution loop called by Windows SCM."""
            setup_logging(console=False)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, "")
            )
            logger.info("ServicePulse Windows Service starting...")

            try:
                agent = ServicePulseAgent()
                self._agent_thread = threading.Thread(
                    target=agent.run,
                    args=(self._stop_event,),
                    name="ServicePulseAgentWorker",
                    daemon=True
                )
                self._agent_thread.start()

                # Wait until Windows Service Manager signals stop
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

                # Wait for agent thread to finish gracefully
                self._stop_event.set()
                if self._agent_thread and self._agent_thread.is_alive():
                    self._agent_thread.join(timeout=5.0)

            except Exception as e:
                logger.error(f"Fatal error in Windows Service execution: {e}", exc_info=True)
                servicemanager.LogErrorMsg(f"ServicePulse Agent error: {e}")
            finally:
                logger.info("ServicePulse Windows Service stopped.")
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, "")
                )
else:
    class ServicePulseWindowsService:
        """Dummy placeholder when pywin32 is not installed or on non-Windows platforms."""
        _svc_name_ = "ServicePulseAgent"
        _svc_display_name_ = "ServicePulse Monitoring Agent"

        def __init__(self, *args, **kwargs):
            pass
