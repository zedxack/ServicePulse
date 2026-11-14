"""
ServicePulse Native Windows Agent - Windows Activation & Licensing Collector
Queries Windows Software Licensing API (SLAPI) / SoftwareLicensingProduct via PowerShell CIM.
Never exposes complete product keys; distinguishes genuinely activated from unavailable states.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import json
import subprocess
import sys
from typing import Optional

from pydantic import BaseModel

from servicepulse.logging.setup import get_logger

logger = get_logger()

# Windows SLAPI LicenseStatus enum mapping
LICENSE_STATUS_MAP = {
    0: "unlicensed",
    1: "licensed",
    2: "oob_grace",
    3: "oot_grace",
    4: "non_genuine_grace",
    5: "notification",
    6: "extended_grace",
}


class WindowsActivationStatus(BaseModel):
    status: str  # "licensed", "not_activated", "in_grace_period", "notification", "unavailable"
    license_status_raw: Optional[int] = None
    product_name: Optional[str] = None
    channel: Optional[str] = None
    partial_key: Optional[str] = None
    is_genuine: Optional[bool] = None
    details: Optional[str] = None


class WindowsActivationCollector:
    """Collects genuine Windows licensing and activation status."""

    QUERY_SCRIPT = (
        "Get-CimInstance SoftwareLicensingProduct -Filter 'PartialProductKey is not null' "
        "| Where-Object { $_.Name -like 'Windows*' } "
        "| Select-Object -First 1 Name, Description, LicenseStatus, PartialProductKey "
        "| ConvertTo-Json"
    )

    @classmethod
    def collect(cls, timeout_seconds: int = 8) -> WindowsActivationStatus:
        """
        Query Windows licensing status with strict timeout protection.
        If non-Windows, timeout, or access denied occurs, reports status='unavailable'.
        """
        if sys.platform != "win32":
            return WindowsActivationStatus(
                status="unavailable",
                details="Windows Activation API is only available on native Windows platforms"
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
            logger.warning(f"Windows activation query timed out after {timeout_seconds}s")
            return WindowsActivationStatus(
                status="unavailable",
                details=f"Query timed out after {timeout_seconds}s"
            )
        except (FileNotFoundError, OSError, PermissionError) as e:
            logger.warning(f"Failed to execute PowerShell for activation query: {e}")
            return WindowsActivationStatus(
                status="unavailable",
                details=f"PowerShell execution failed: {e}"
            )

        if result.returncode != 0 or not result.stdout.strip():
            logger.debug(f"PowerShell returned non-zero code {result.returncode}: {result.stderr.strip()}")
            return WindowsActivationStatus(
                status="unavailable",
                details=f"Query failed with code {result.returncode}"
            )

        try:
            data = json.loads(result.stdout.strip())
            # If multiple returned as array, pick the first Windows OS entry
            if isinstance(data, list):
                if not data:
                    return WindowsActivationStatus(status="unavailable", details="Empty licensing result")
                data = data[0]

            lic_status = data.get("LicenseStatus")
            raw_status_name = LICENSE_STATUS_MAP.get(lic_status, "unknown")
            product_name = data.get("Name")
            desc = data.get("Description")
            partial_key = data.get("PartialProductKey")

            # Validate partial key: max 5 alphanumeric chars
            safe_partial = None
            if partial_key and isinstance(partial_key, str) and len(partial_key.strip()) <= 5:
                safe_partial = partial_key.strip()

            if lic_status == 1:
                status_str = "licensed"
                is_genuine = True
            elif lic_status in (2, 3, 6):
                status_str = "in_grace_period"
                is_genuine = False
            elif lic_status == 5:
                status_str = "notification"
                is_genuine = False
            elif lic_status == 0:
                status_str = "not_activated"
                is_genuine = False
            elif lic_status == 4:
                status_str = "non_genuine"
                is_genuine = False
            else:
                status_str = raw_status_name
                is_genuine = False

            return WindowsActivationStatus(
                status=status_str,
                license_status_raw=lic_status,
                product_name=product_name,
                channel=desc,
                partial_key=safe_partial,
                is_genuine=is_genuine,
                details=f"{product_name} ({desc})" if product_name else None
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse activation JSON: {e}")
            return WindowsActivationStatus(
                status="unavailable",
                details=f"JSON parsing error: {e}"
            )
