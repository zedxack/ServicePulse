"""
ServicePulse Native Windows Agent - Structured Logging Setup
Ensures credentials, bearer tokens, and secrets are never exposed in log outputs.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Sensitive patterns to redact in log messages
_SENSITIVE_PATTERNS = [
    (re.compile(r"(token[\"':\s=]+)(sp_tok_[a-zA-Z0-9_\-]+)", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(secret[\"':\s=]+)([a-zA-Z0-9_\-]{8,})", re.IGNORECASE), r"\1[REDACTED_SECRET]"),
    (re.compile(r"(X-Agent-Token[\"':\s=]+)([^\s,}\"]+)", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(Authorization:\s*Bearer\s+)([^\s,}\"]+)", re.IGNORECASE), r"\1[REDACTED_BEARER]"),
    (re.compile(r"([0-9A-Z]{5}-[0-9A-Z]{5}-[0-9A-Z]{5}-[0-9A-Z]{5}-[0-9A-Z]{5})", re.IGNORECASE), "[REDACTED_PRODUCT_KEY]"),
]


class SensitiveFilter(logging.Filter):
    """Filter that sanitizes log records containing sensitive authentication tokens or product keys."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            sanitized = record.msg
            for pattern, repl in _SENSITIVE_PATTERNS:
                sanitized = pattern.sub(repl, sanitized)
            record.msg = sanitized
        return True


def get_default_log_dir() -> Path:
    """Return appropriate platform-specific log directory."""
    if os.name == "nt":
        prog_data = os.environ.get("ProgramData", r"C:\ProgramData")
        target = Path(prog_data) / "ServicePulse" / "logs"
    else:
        target = Path("logs")

    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except (PermissionError, OSError):
        local_target = Path("logs")
        local_target.mkdir(parents=True, exist_ok=True)
        return local_target


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    console: bool = True
) -> logging.Logger:
    """
    Configure root agent logging with rotating file handler and sensitive data filtering.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("servicepulse_agent")
    logger.setLevel(numeric_level)
    logger.propagate = False

    # Prevent duplicate handlers on re-initialization
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    sensitive_filter = SensitiveFilter()

    # 1. Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        logger.addHandler(console_handler)

    # 2. Rotating file handler (10 MB max, keep 5 backups)
    actual_dir = log_dir or get_default_log_dir()
    log_file = actual_dir / "servicepulse_agent.log"
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        logger.warning(f"Could not initialize log file at {log_file}: {e}")

    return logger


def get_logger() -> logging.Logger:
    """Retrieve the ServicePulse agent logger."""
    return logging.getLogger("servicepulse_agent")
