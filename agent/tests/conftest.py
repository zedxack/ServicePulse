"""
ServicePulse Windows Agent - Test Configuration & Fixtures
Author: Muhammadyusuf Usmonov
"""
import sys
from pathlib import Path

import pytest

# Ensure 'agent' and project root are in sys.path
agent_root = Path(__file__).resolve().parent.parent
project_root = agent_root.parent
if str(agent_root) not in sys.path:
    sys.path.insert(0, str(agent_root))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from servicepulse.authentication import AgentCredentials, CredentialStore  # noqa: E402
from servicepulse.config import AgentConfig  # noqa: E402
from servicepulse.queue.storage import QueueStorage  # noqa: E402


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated temporary directory for agent data/queue/credentials."""
    data_dir = tmp_path / "servicepulse_test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def test_config(tmp_data_dir: Path) -> AgentConfig:
    """Fixture providing AgentConfig pointed to test data directory."""
    return AgentConfig(
        server_url="http://localhost:8000",
        agent_name="TEST-WIN11-NODE",
        heartbeat_interval_seconds=5,
        telemetry_interval_seconds=10,
        command_poll_interval_seconds=5,
        request_timeout_seconds=5,
        offline_queue_max_records=500,
        log_level="DEBUG",
        verify_ssl=False,
        data_dir=str(tmp_data_dir),
    )


@pytest.fixture
def test_cred_store(tmp_data_dir: Path) -> CredentialStore:
    """Fixture providing an isolated CredentialStore."""
    return CredentialStore(tmp_data_dir / "credentials.dat")


@pytest.fixture
def sample_credentials() -> AgentCredentials:
    """Fixture providing sample valid credentials."""
    return AgentCredentials(
        agent_uuid="agent_test_uuid_12345",
        api_token="sp_tok_test_token_secret_abcdef123456",
        device_id=42,
        organization_id=1,
    )


@pytest.fixture
def test_queue_storage(tmp_data_dir: Path) -> QueueStorage:
    """Fixture providing an isolated QueueStorage."""
    return QueueStorage(tmp_data_dir / "test_queue.db")
