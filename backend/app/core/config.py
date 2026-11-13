"""
ServicePulse - Core Application Configuration
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import json
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "ServicePulse"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = Field(
        default="insecure-default-change-in-production-servicepulse-security-token-key",
        description="JWT secret signing key"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Agent Enrollment
    AGENT_ENROLLMENT_SECRET: str = "servicepulse-agent-enrollment-secret-2026"

    # Initial Administrative & Seed Credentials (override via .env)
    FIRST_SUPERUSER_EMAIL: str = "admin@servicepulse.uz"
    FIRST_SUPERUSER_PASSWORD: str = "AdminPass2026!"
    FIRST_SUPPORT_EMAIL: str = "support@servicepulse.uz"
    FIRST_SUPPORT_PASSWORD: str = "SupportPass2026!"
    FIRST_EMPLOYEE_EMAIL: str = "employee@servicepulse.uz"
    FIRST_EMPLOYEE_PASSWORD: str = "EmployeePass2026!"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # Validate that production environments use secure non-default secrets
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and ("insecure-default" in v or len(v) < 32):
            raise ValueError("In production mode, SECRET_KEY must be a secure key with at least 32 characters.")
        return v

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./servicepulse.db"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_password_2026"
    POSTGRES_DB: str = "servicepulse"

    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:80"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return []

    # Monitoring & Worker Defaults
    MONITORING_INTERVAL_SECONDS: int = 30
    CONSECUTIVE_FAILURE_THRESHOLD: int = 3
    PING_TIMEOUT_SECONDS: int = 2
    TCP_TIMEOUT_SECONDS: int = 3

    # Automated Remediation
    ENABLE_AUTOMATED_REMEDIATION: bool = True
    MAX_REMEDIATION_RETRIES: int = 2
    REMEDIATION_COOLDOWN_SECONDS: int = 300

    # Service Level Agreement (SLA) Configuration
    SLA_TARGET_PERCENT: float = 99.5

    # Approved Enterprise Software Catalog
    APPROVED_SOFTWARE_CATALOG: List[str] = [
        "7-Zip",
        "Google Chrome",
        "Mozilla Firefox",
        "Visual Studio Code",
        "Git",
        "Python",
        "Node.js",
        "LibreOffice",
        "VLC Media Player",
        "Wireshark",
        "Wireshark Network Analyzer",
        "PuTTY",
        "WinSCP",
    ]


settings = Settings()
