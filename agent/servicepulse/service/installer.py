"""
ServicePulse Native Windows Agent - Windows Service Lifecycle Manager
Handles installation, uninstallation, start, stop, and status querying of the Windows Service.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import subprocess
import sys
from typing import Dict, Optional

from servicepulse.logging.setup import get_logger

logger = get_logger()

SERVICE_NAME = "ServicePulseAgent"


class ServiceManager:
    """Manages the Windows Service installation and status via sc.exe."""

    @staticmethod
    def is_windows() -> bool:
        return sys.platform == "win32"

    @classmethod
    def get_service_status(cls) -> Dict[str, str]:
        """Query current Windows Service status via sc.exe."""
        if not cls.is_windows():
            return {"installed": "false", "status": "unavailable", "message": "Non-Windows platform"}

        try:
            res = subprocess.run(
                ["sc.exe", "query", SERVICE_NAME],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                check=False
            )
            stdout = res.stdout
            if "FAILED 1060" in stdout or "The specified service does not exist" in stdout or res.returncode == 1060:
                return {"installed": "false", "status": "not_installed", "message": "Service is not installed"}

            status_str = "unknown"
            if "RUNNING" in stdout:
                status_str = "running"
            elif "STOPPED" in stdout:
                status_str = "stopped"
            elif "START_PENDING" in stdout:
                status_str = "start_pending"
            elif "STOP_PENDING" in stdout:
                status_str = "stop_pending"

            return {"installed": "true", "status": status_str, "message": stdout.strip()}
        except Exception as e:
            return {"installed": "unknown", "status": "error", "message": str(e)}

    @classmethod
    def install_service(cls, python_executable: Optional[str] = None, script_path: Optional[str] = None) -> bool:
        """Install ServicePulse as a Windows Service."""
        if not cls.is_windows():
            logger.error("Service installation is only supported on Windows.")
            return False

        try:
            import win32serviceutil

            from servicepulse.service.windows_service import ServicePulseWindowsService

            win32serviceutil.InstallService(
                ServicePulseWindowsService._svc_name_,
                ServicePulseWindowsService._svc_name_,
                ServicePulseWindowsService._svc_display_name_,
                startType=win32serviceutil.win32service.SERVICE_AUTO_START,
                description=ServicePulseWindowsService._svc_description_
            )
            logger.info("ServicePulse Windows Service installed successfully.")
            return True
        except PermissionError:
            logger.error("Administrator elevation required to install Windows Service. Run PowerShell or CMD as Administrator.")
            return False
        except Exception as e:
            logger.error(f"Failed to install service via win32serviceutil: {e}")
            return False

    @classmethod
    def uninstall_service(cls) -> bool:
        """Remove ServicePulse Windows Service."""
        if not cls.is_windows():
            logger.error("Service uninstallation is only supported on Windows.")
            return False

        try:
            import win32serviceutil

            from servicepulse.service.windows_service import ServicePulseWindowsService

            win32serviceutil.RemoveService(ServicePulseWindowsService._svc_name_)
            logger.info("ServicePulse Windows Service removed successfully.")
            return True
        except PermissionError:
            logger.error("Administrator elevation required to uninstall Windows Service.")
            return False
        except Exception as e:
            logger.error(f"Failed to uninstall service: {e}")
            return False

    @classmethod
    def start_service(cls) -> bool:
        """Start the Windows Service via sc.exe."""
        if not cls.is_windows():
            return False

        try:
            res = subprocess.run(
                ["sc.exe", "start", SERVICE_NAME],
                capture_output=True,
                text=True,
                shell=False,
                timeout=10,
                check=False
            )
            if res.returncode == 0 or "START_PENDING" in res.stdout:
                logger.info("ServicePulse Windows Service start issued successfully.")
                return True
            else:
                logger.error(f"Failed to start service: {res.stdout.strip()}")
                return False
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            return False

    @classmethod
    def stop_service(cls) -> bool:
        """Stop the Windows Service via sc.exe."""
        if not cls.is_windows():
            return False

        try:
            res = subprocess.run(
                ["sc.exe", "stop", SERVICE_NAME],
                capture_output=True,
                text=True,
                shell=False,
                timeout=10,
                check=False
            )
            if res.returncode == 0 or "STOP_PENDING" in res.stdout:
                logger.info("ServicePulse Windows Service stop issued successfully.")
                return True
            else:
                logger.error(f"Failed to stop service: {res.stdout.strip()}")
                return False
        except Exception as e:
            logger.error(f"Error stopping service: {e}")
            return False

    @classmethod
    def restart_service(cls) -> bool:
        """Stop and restart the Windows Service."""
        cls.stop_service()
        import time
        time.sleep(2)
        return cls.start_service()
