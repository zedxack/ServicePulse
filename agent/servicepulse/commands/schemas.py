"""
ServicePulse Native Windows Agent - Command Parameter Pydantic Schemas
Strictly validates command parameter payloads against security rules.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import json
import re
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from servicepulse.commands.allowlist import (
    IP_OR_HOST_REGEX,
    SERVICE_NAME_REGEX,
    VERSION_REGEX,
    CommandAllowlist,
)

SHA256_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")


class RestartServiceParams(BaseModel):
    service_name: str = Field(..., max_length=64)

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        clean = v.strip()
        if not SERVICE_NAME_REGEX.match(clean):
            raise ValueError("Service name contains illegal characters or metacharacters")
        if not CommandAllowlist.is_service_allowed(clean):
            raise ValueError(f"Service '{clean}' is not in the allowed remediation services list")
        return clean


class RestartAgentParams(BaseModel):
    reason: Optional[str] = Field("Scheduled administrator remediation", max_length=150)
    delay_seconds: int = Field(default=2, ge=0, le=60)


class DiagnosticCheckParams(BaseModel):
    check_type: Literal["ping", "dns", "tcp", "disk", "service"] = Field(...)
    target: Optional[str] = Field(None, max_length=150)

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not IP_OR_HOST_REGEX.match(clean):
                raise ValueError("Diagnostic target contains illegal characters or shell metacharacters")
            return clean
        return None


class RecheckNetworkParams(BaseModel):
    target: str = Field(..., max_length=150)
    port: Optional[int] = Field(None, ge=1, le=65535)
    protocol: Literal["icmp", "tcp"] = Field(default="icmp")

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        clean = v.strip()
        if not IP_OR_HOST_REGEX.match(clean):
            raise ValueError("Network endpoint target contains invalid characters or shell metacharacters")
        return clean


class NotifyAdminParams(BaseModel):
    message: str = Field(..., max_length=500)
    severity: Literal["info", "warning", "critical"] = Field(default="info")


class InstallApprovedSoftwareParams(BaseModel):
    software: str = Field(..., max_length=100)
    version: Optional[str] = Field(None, max_length=30)
    sha256: Optional[str] = Field(None, max_length=64)
    download_url: Optional[str] = Field(None, max_length=500)

    @field_validator("software")
    @classmethod
    def validate_software(cls, v: str) -> str:
        clean = v.strip()
        if not CommandAllowlist.is_software_approved(clean):
            raise ValueError(f"Software '{clean}' is not in the approved software catalog")
        return clean

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            clean = v.strip()
            if not VERSION_REGEX.match(clean):
                raise ValueError("Software version contains illegal characters or shell metacharacters")
            return clean
        return None

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            clean = v.strip().lower()
            if not SHA256_REGEX.match(clean):
                raise ValueError("Cryptographic sha256 checksum must be a valid 64-character hexadecimal string")
            return clean
        return None

    @field_validator("download_url")
    @classmethod
    def validate_download_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            clean = v.strip()
            if not clean.startswith("https://"):
                raise ValueError("Download URL must use secure HTTPS protocol")
            return clean
        return None


def parse_and_validate_command_parameters(
    action_name: str,
    raw_params: Union[str, Dict[str, Any], None]
) -> BaseModel:
    """
    Parse JSON or dictionary parameters into the strictly typed Pydantic schema for the action.
    Raises ValueError on validation or schema failure.
    """
    if not CommandAllowlist.is_action_allowed(action_name):
        raise ValueError(f"Action '{action_name}' is not permitted by local security policy")

    parsed_dict: Dict[str, Any] = {}
    if isinstance(raw_params, str) and raw_params.strip():
        try:
            parsed_dict = json.loads(raw_params)
        except json.JSONDecodeError as e:
            raise ValueError(f"Command parameters must be valid JSON: {e}") from e
    elif isinstance(raw_params, dict):
        parsed_dict = raw_params

    # Route to action schema
    if action_name == "restart_service":
        return RestartServiceParams(**parsed_dict)
    elif action_name == "restart_servicepulse_agent":
        return RestartAgentParams(**parsed_dict)
    elif action_name == "run_diagnostic_check":
        return DiagnosticCheckParams(**parsed_dict)
    elif action_name == "recheck_network_endpoint":
        return RecheckNetworkParams(**parsed_dict)
    elif action_name == "notify_administrator":
        return NotifyAdminParams(**parsed_dict)
    elif action_name == "install_approved_software":
        return InstallApprovedSoftwareParams(**parsed_dict)
    else:
        raise ValueError(f"Unsupported action: {action_name}")
