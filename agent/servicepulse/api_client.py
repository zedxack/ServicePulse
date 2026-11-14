"""
ServicePulse Native Windows Agent - Backend API Client
Manages HTTP/HTTPS communication with ServicePulse backend API.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
from typing import Any, Dict, List, Optional

import httpx

from servicepulse import __version__
from servicepulse.authentication import AgentCredentials
from servicepulse.config import AgentConfig
from servicepulse.logging.setup import get_logger

logger = get_logger()


class AgentApiError(Exception):
    """Base exception for ServicePulse Agent API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AgentAuthError(AgentApiError):
    """Authentication or authorization failure (HTTP 401 or 403)."""
    pass


class AgentConnectionError(AgentApiError):
    """Network connection failure or timeout reaching the backend."""
    pass


class ApiClient:
    """
    Synchronous HTTP client for ServicePulse backend API.
    Designed for reliability, structured error handling, and offline fallback.
    """

    def __init__(self, config: AgentConfig, credentials: Optional[AgentCredentials] = None):
        self.config = config
        self.credentials = credentials
        self.base_url = config.server_url.rstrip("/")
        self._session = httpx.Client(
            timeout=config.request_timeout_seconds,
            verify=config.verify_ssl,
            headers={
                "User-Agent": f"ServicePulse-Agent/{__version__} (Windows; x64)",
                "Accept": "application/json",
            }
        )

    def set_credentials(self, credentials: AgentCredentials) -> None:
        """Update authenticated credentials for subsequent calls."""
        self.credentials = credentials

    def _get_auth_headers(self) -> Dict[str, str]:
        """Construct authentication headers."""
        if not self.credentials or not self.credentials.api_token:
            raise AgentAuthError("No credentials configured for authenticated API request")
        return {
            "X-Agent-Token": self.credentials.api_token,
            "Authorization": f"Bearer {self.credentials.api_token}",
        }

    def enroll(
        self,
        enrollment_secret: str,
        hostname: str,
        ip_address: str,
        os_name: Optional[str] = None,
        version: str = __version__,
        device_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> AgentCredentials:
        """
        Enroll this agent against the backend using pre-shared enrollment secret.
        Returns newly provisioned AgentCredentials.
        """
        url = f"{self.base_url}/api/v1/agent/enroll"
        payload = {
            "enrollment_secret": enrollment_secret,
            "hostname": hostname,
            "ip_address": ip_address,
            "os_name": os_name,
            "version": version,
            "device_id": device_id,
            "organization_id": organization_id,
        }

        try:
            resp = self._session.post(url, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Failed to connect to enrollment server at {url}: {e}") from e

        if resp.status_code == 201:
            data = resp.json()
            creds = AgentCredentials(
                agent_uuid=data["agent_uuid"],
                api_token=data["api_token"],
                device_id=data.get("device_id"),
                organization_id=data.get("organization_id"),
            )
            self.set_credentials(creds)
            logger.info(f"Agent successfully enrolled with UUID: {creds.agent_uuid}")
            return creds
        elif resp.status_code in (401, 403):
            raise AgentAuthError(f"Enrollment rejected: {resp.text}", status_code=resp.status_code, response_body=resp.text)
        else:
            raise AgentApiError(f"Enrollment failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code, response_body=resp.text)

    def heartbeat(self, agent_version: str = __version__, ip_address: Optional[str] = None) -> bool:
        """Send periodic keepalive heartbeat ping."""
        url = f"{self.base_url}/api/v1/agent/heartbeat"
        headers = self._get_auth_headers()
        payload = {
            "agent_version": agent_version,
            "ip_address": ip_address,
        }

        try:
            resp = self._session.post(url, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Heartbeat connection failure: {e}") from e

        if resp.status_code == 200:
            return True
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Heartbeat rejected: Agent token invalid or revoked", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Heartbeat failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def submit_telemetry(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit system telemetry record.
        Handles server-side idempotency and duplicate notices gracefully.
        """
        url = f"{self.base_url}/api/v1/agent/telemetry"
        headers = self._get_auth_headers()

        try:
            resp = self._session.post(url, json=telemetry_data, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Telemetry submission connection failure: {e}") from e

        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Telemetry submission rejected: Agent token invalid or revoked", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Telemetry submission failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def get_me(self) -> Dict[str, Any]:
        """Retrieve current agent status from backend."""
        url = f"{self.base_url}/api/v1/agent/me"
        headers = self._get_auth_headers()

        try:
            resp = self._session.get(url, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Failed to contact backend: {e}") from e

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Authentication failed retrieving agent info", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Failed to get agent info with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Poll queued commands for this agent."""
        url = f"{self.base_url}/api/v1/agent/me/commands?status=pending"
        headers = self._get_auth_headers()

        try:
            resp = self._session.get(url, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Command poll connection failure: {e}") from e

        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Command poll rejected: Agent token invalid or revoked", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Command poll failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def acknowledge_command(self, command_id: int) -> bool:
        """Acknowledge command receipt."""
        url = f"{self.base_url}/api/v1/agent/me/commands/{command_id}/ack"
        headers = self._get_auth_headers()

        try:
            resp = self._session.post(url, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Command ack connection failure: {e}") from e

        if resp.status_code == 200:
            return True
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Command ack rejected: Unauthorized", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Command ack failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def report_command_result(
        self,
        command_id: int,
        status: str,
        execution_result: str,
        executed_at: Optional[str] = None
    ) -> bool:
        """Submit command execution result."""
        url = f"{self.base_url}/api/v1/agent/me/commands/{command_id}/result"
        headers = self._get_auth_headers()
        payload = {
            "status": status,
            "execution_result": execution_result,
            "executed_at": executed_at,
        }

        try:
            resp = self._session.post(url, json=payload, headers=headers)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise AgentConnectionError(f"Command result reporting connection failure: {e}") from e

        if resp.status_code == 200:
            return True
        elif resp.status_code in (401, 403):
            raise AgentAuthError("Command result submission rejected: Unauthorized", status_code=resp.status_code)
        else:
            raise AgentApiError(f"Command result reporting failed with HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def close(self) -> None:
        """Close underlying HTTP client session."""
        self._session.close()
