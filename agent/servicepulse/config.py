"""
ServicePulse Native Windows Agent - Configuration Manager
Loads validated settings from configuration files and environment variables.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import json
import os
import socket
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def get_default_data_dir() -> Path:
    """Return default data directory for agent credentials, queue DB, and state."""
    if os.name == "nt":
        prog_data = os.environ.get("ProgramData", r"C:\ProgramData")
        target = Path(prog_data) / "ServicePulse"
    else:
        target = Path("data")

    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except (PermissionError, OSError):
        local_target = Path("data")
        local_target.mkdir(parents=True, exist_ok=True)
        return local_target


class AgentConfig(BaseModel):
    """Configuration model for ServicePulse Windows Agent."""
    server_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of ServicePulse backend API"
    )
    agent_name: str = Field(
        default_factory=socket.gethostname,
        max_length=150,
        description="Identifier name for the local endpoint"
    )
    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        description="Heartbeat ping frequency"
    )
    telemetry_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=86400,
        description="System telemetry collection frequency"
    )
    command_poll_interval_seconds: int = Field(
        default=15,
        ge=3,
        le=3600,
        description="Remediation command poll frequency"
    )
    request_timeout_seconds: int = Field(
        default=10,
        ge=2,
        le=120,
        description="HTTP request timeout in seconds"
    )
    offline_queue_max_records: int = Field(
        default=10000,
        ge=100,
        le=500000,
        description="Maximum uncommitted telemetry records in offline SQLite queue"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Enforce SSL/TLS certificate verification on HTTPS connections"
    )
    ca_bundle_path: Optional[str] = Field(
        default=None,
        description="Path to custom enterprise CA certificate bundle"
    )
    data_dir: Optional[str] = Field(
        default=None,
        description="Custom directory for credentials and offline queue"
    )

    @field_validator("server_url")
    @classmethod
    def validate_server_url(cls, v: str) -> str:
        clean = v.strip().rstrip("/")
        if not (clean.startswith("http://") or clean.startswith("https://")):
            raise ValueError("server_url must begin with http:// or https://")
        return clean

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.strip().upper()
        if upper_v not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper_v

    def get_data_directory(self) -> Path:
        """Resolve actual data directory path."""
        if self.data_dir:
            p = Path(self.data_dir)
            p.mkdir(parents=True, exist_ok=True)
            return p
        return get_default_data_dir()

    def get_credentials_path(self) -> Path:
        """Path to DPAPI-protected credentials file."""
        return self.get_data_directory() / "credentials.dat"

    def get_queue_db_path(self) -> Path:
        """Path to offline SQLite queue database."""
        return self.get_data_directory() / "telemetry_queue.db"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AgentConfig":
        """
        Load configuration from file or default locations with environment variable overrides.
        """
        data = {}

        # Look in specified or candidate paths
        search_paths = []
        if config_path:
            search_paths.append(config_path)
        else:
            search_paths.extend([
                Path("config.json"),
                Path("agent/config.json"),
                get_default_data_dir() / "config.json",
            ])

        for p in search_paths:
            if p and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    break
                except Exception:
                    pass

        # Environment variable overrides
        env_map = {
            "SERVICEPULSE_SERVER_URL": "server_url",
            "SERVICEPULSE_AGENT_NAME": "agent_name",
            "SERVICEPULSE_HEARTBEAT_INTERVAL": "heartbeat_interval_seconds",
            "SERVICEPULSE_TELEMETRY_INTERVAL": "telemetry_interval_seconds",
            "SERVICEPULSE_COMMAND_POLL_INTERVAL": "command_poll_interval_seconds",
            "SERVICEPULSE_REQUEST_TIMEOUT": "request_timeout_seconds",
            "SERVICEPULSE_QUEUE_MAX_RECORDS": "offline_queue_max_records",
            "SERVICEPULSE_LOG_LEVEL": "log_level",
            "SERVICEPULSE_VERIFY_SSL": "verify_ssl",
            "SERVICEPULSE_DATA_DIR": "data_dir",
        }

        for env_var, field_name in env_map.items():
            val = os.environ.get(env_var)
            if val is not None:
                if field_name in ("heartbeat_interval_seconds", "telemetry_interval_seconds", "command_poll_interval_seconds", "request_timeout_seconds", "offline_queue_max_records"):
                    data[field_name] = int(val)
                elif field_name == "verify_ssl":
                    data[field_name] = val.lower() in ("true", "1", "yes")
                else:
                    data[field_name] = val

        return cls(**data)
