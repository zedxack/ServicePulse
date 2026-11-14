"""
ServicePulse Native Windows Agent - Secure Enrollment Flow
Registers the local machine with the ServicePulse platform and saves DPAPI-protected credentials.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import socket
from typing import Optional

from servicepulse import __version__
from servicepulse.api_client import ApiClient
from servicepulse.authentication import AgentCredentials, CredentialStore
from servicepulse.collectors.network import NetworkCollector
from servicepulse.collectors.system import SystemCollector
from servicepulse.config import AgentConfig
from servicepulse.logging.setup import get_logger

logger = get_logger()


class EnrollmentManager:
    """Handles agent initial registration and credential storage."""

    @classmethod
    def enroll_agent(
        cls,
        config: AgentConfig,
        enrollment_secret: str,
        device_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> AgentCredentials:
        """
        Execute enrollment against backend API and store returned credentials in DPAPI vault.
        """
        logger.info(f"Initiating agent enrollment against {config.server_url}...")

        hostname = config.agent_name or socket.gethostname()
        primary_ip = NetworkCollector.get_primary_ip()
        os_info = SystemCollector.collect_os()
        os_name = f"{os_info.os_name} {os_info.os_version}".strip()

        api_client = ApiClient(config)
        try:
            creds = api_client.enroll(
                enrollment_secret=enrollment_secret,
                hostname=hostname,
                ip_address=primary_ip,
                os_name=os_name,
                version=__version__,
                device_id=device_id,
                organization_id=organization_id,
            )
        finally:
            api_client.close()

        # Save credentials in DPAPI store
        store = CredentialStore(config.get_credentials_path())
        store.save_credentials(creds)
        logger.info(f"Enrollment successful. Agent UUID: {creds.agent_uuid}")
        return creds
