"""
ServicePulse Native Windows Agent - Windows Defender Status Collector
Queries Windows Defender status safely using read-only Get-MpComputerStatus PowerShell cmdlet.
Never modifies firewall, security, or antivirus settings.
Author: Muhammadyusuf Usmonov
"""
import json
import subprocess
import sys
from typing import Optional

from pydantic import BaseModel

from servicepulse.logging.setup import get_logger

logger = get_logger()


class DefenderStatus(BaseModel):
    status: str  # "healthy", "realtime_disabled", "antivirus_disabled", "signatures_outdated", "unavailable"
    antivirus_enabled: Optional[bool] = None
    realtime_protection_enabled: Optional[bool] = None
    antispyware_enabled: Optional[bool] = None
    signature_age_days: Optional[int] = None
    details: Optional[str] = None


class DefenderCollector:
    """Collects read-only Windows Defender antivirus and protection status."""

    QUERY_SCRIPT = (
        "Get-MpComputerStatus "
        "| Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntispywareEnabled, AntivirusSignatureAge "
        "| ConvertTo-Json"
    )

    @classmethod
    def collect(cls, timeout_seconds: int = 8) -> DefenderStatus:
        """
        Query Windows Defender protection status with timeout protection.
        If non-Windows, timeout, or access denied occurs, reports status='unavailable'.
        """
        if sys.platform != "win32":
            return DefenderStatus(
                status="unavailable",
                details="Windows Defender monitoring is only supported on native Windows platforms"
            )

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", cls.QUERY_SCRIPT
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Defender status query timed out after {timeout_seconds}s")
            return DefenderStatus(
                status="unavailable",
                details=f"Query timed out after {timeout_seconds}s"
            )
        except (FileNotFoundError, OSError, PermissionError) as e:
            logger.warning(f"Failed to execute PowerShell for Defender query: {e}")
            return DefenderStatus(
                status="unavailable",
                details=f"PowerShell execution failed: {e}"
            )

        if result.returncode != 0 or not result.stdout.strip():
            logger.debug(f"PowerShell returned non-zero code {result.returncode}: {result.stderr.strip()}")
            return DefenderStatus(
                status="unavailable",
                details=f"Query failed with exit code {result.returncode}"
            )

        try:
            data = json.loads(result.stdout.strip())
            av_enabled = data.get("AntivirusEnabled")
            rt_enabled = data.get("RealTimeProtectionEnabled")
            as_enabled = data.get("AntispywareEnabled")
            sig_age = data.get("AntivirusSignatureAge")

            if sig_age is not None:
                try:
                    sig_age = int(sig_age)
                except (ValueError, TypeError):
                    sig_age = None

            # Determine composite status
            if av_enabled is False:
                status_str = "antivirus_disabled"
                details = "Antivirus engine is disabled"
            elif rt_enabled is False:
                status_str = "realtime_disabled"
                details = "Real-time protection is disabled"
            elif sig_age is not None and sig_age > 14:
                status_str = "signatures_outdated"
                details = f"Antivirus signatures are {sig_age} days old"
            elif av_enabled and rt_enabled:
                status_str = "healthy"
                details = f"All protections active (signatures {sig_age or 0}d old)"
            else:
                status_str = "healthy"
                details = "Protections active"

            return DefenderStatus(
                status=status_str,
                antivirus_enabled=av_enabled,
                realtime_protection_enabled=rt_enabled,
                antispyware_enabled=as_enabled,
                signature_age_days=sig_age,
                details=details
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse Defender JSON output: {e}")
            return DefenderStatus(
                status="unavailable",
                details=f"JSON parsing error: {e}"
            )
