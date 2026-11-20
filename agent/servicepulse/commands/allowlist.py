"""
ServicePulse Native Windows Agent - Security Allowlist & Restrictions
Strict local allowlist of authorized actions, safe services, and approved software packages.
Author: Muhammadyusuf Usmonov
"""
import re
from typing import Set

# Authorized remediation and diagnostic action names
ALLOWED_ACTIONS: Set[str] = {
    "restart_service",
    "restart_servicepulse_agent",
    "run_diagnostic_check",
    "recheck_network_endpoint",
    "notify_administrator",
    "install_approved_software",
}

# Allowlisted Windows services that can be safely restarted by the Agent
ALLOWED_SERVICES: Set[str] = {
    "wuauserv",             # Windows Update
    "spooler",              # Print Spooler
    "servicepulseagent",    # ServicePulse Agent
    "servicepulse",         # ServicePulse
    "w32time",              # Windows Time
    "dnscache",             # DNS Client Cache
    "lanmanworkstation",    # Workstation Network Client
    "audiosrv",             # Windows Audio Service
    "themes",               # Desktop Themes
    "bits",                 # Background Intelligent Transfer Service
    "wscsvc",               # Windows Security Center Service
}

# Critical system services that must NEVER be stopped or restarted
PROHIBITED_SERVICES: Set[str] = {
    "lsass", "csrss", "smss", "winlogon", "services", "system", "registry", "samss"
}

# Approved enterprise software catalog matching backend policy
APPROVED_SOFTWARE_CATALOG: Set[str] = {
    "7-zip",
    "google chrome",
    "mozilla firefox",
    "visual studio code",
    "git",
    "python",
    "node.js",
    "libreoffice",
    "vlc media player",
    "wireshark",
    "wireshark network analyzer",
    "putty",
    "winscp",
}

# Regex to prevent shell metacharacter injection
SERVICE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")
VERSION_REGEX = re.compile(r"^[a-zA-Z0-9\.\-_+]{1,30}$")
IP_OR_HOST_REGEX = re.compile(r"^[a-zA-Z0-9\.\-_]{1,150}$")


class CommandAllowlist:
    """Security allowlist validator for incoming agent commands."""

    @classmethod
    def is_action_allowed(cls, action_name: str) -> bool:
        """Check if action is in the strict allowlist."""
        return action_name.strip().lower() in ALLOWED_ACTIONS

    @classmethod
    def is_service_allowed(cls, service_name: str) -> bool:
        """
        Validate whether a Windows service identifier is permitted for remediation.
        Rejects prohibited system components and any string with shell metacharacters.
        """
        clean_name = service_name.strip().lower()
        if not SERVICE_NAME_REGEX.match(clean_name):
            return False

        if clean_name in PROHIBITED_SERVICES:
            return False

        # Must either match allowed set or start with servicepulse prefix
        if clean_name in ALLOWED_SERVICES or clean_name.startswith("servicepulse"):
            return True

        return False

    @classmethod
    def is_software_approved(cls, software_name: str) -> bool:
        """Validate whether the software title belongs to the approved enterprise catalog."""
        clean_title = software_name.strip().lower()
        return clean_title in APPROVED_SOFTWARE_CATALOG
