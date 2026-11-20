"""
ServicePulse Native Windows Agent - Command Execution Verification
Performs post-execution verification to prove observable system remediation.
Author: Muhammadyusuf Usmonov
"""
import subprocess
import sys
from typing import Tuple

from servicepulse.commands.schemas import RestartServiceParams
from servicepulse.logging.setup import get_logger

logger = get_logger()


class CommandVerifier:
    """Independent verification routines executed after remediation actions."""

    @classmethod
    def verify_service_running(cls, params: RestartServiceParams, simulation: bool = False) -> Tuple[bool, str]:
        """Verify that the restarted service is currently in RUNNING state."""
        if simulation or sys.platform != "win32":
            return True, f"SIMULATION: Service '{params.service_name}' verified in RUNNING state."

        try:
            res = subprocess.run(
                ["sc.exe", "query", params.service_name],
                capture_output=True,
                text=True,
                shell=False,
                timeout=5,
                check=False
            )
            if "RUNNING" in res.stdout:
                return True, f"Verified: Service '{params.service_name}' is in RUNNING state."
            else:
                return False, f"Verification failed: Service '{params.service_name}' is not RUNNING."
        except Exception as e:
            return False, f"Verification error: {e}"
