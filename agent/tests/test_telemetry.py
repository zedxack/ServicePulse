"""
ServicePulse Windows Agent - Telemetry Aggregator Test Suite
Verifies backend payload formatting, idempotency keys, and error tolerance.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
from unittest.mock import patch

from servicepulse.telemetry import TelemetryAggregator

from backend.app.schemas.agent import AgentTelemetryRequest


def test_telemetry_payload_schema_compliance():
    """Verify aggregated payload strictly satisfies backend AgentTelemetryRequest schema."""
    payload = TelemetryAggregator.collect_payload(idempotency_key="tx-test-idemp-001")

    # Validate with Pydantic schema
    req = AgentTelemetryRequest(**payload)
    assert 0.0 <= req.cpu_percent <= 100.0
    assert 0.0 <= req.ram_percent <= 100.0
    assert req.ram_total_mb > 0.0
    assert req.disk_total_gb > 0.0
    assert req.idempotency_key == "tx-test-idemp-001"
    assert req.recorded_at is not None


def test_telemetry_payload_idempotency_generation():
    """Verify unique idempotency keys are auto-generated when omitted."""
    p1 = TelemetryAggregator.collect_payload()
    p2 = TelemetryAggregator.collect_payload()

    assert p1["idempotency_key"] != ""
    assert p2["idempotency_key"] != ""
    assert p1["idempotency_key"] != p2["idempotency_key"]


@patch("servicepulse.collectors.system.SystemCollector.collect_all")
def test_telemetry_collector_resilience_to_failures(mock_collect):
    """Verify telemetry aggregator does not crash if a collector raises an exception."""
    mock_collect.side_effect = RuntimeError("Hardware sensor failure")

    payload = TelemetryAggregator.collect_payload(idempotency_key="resilient-key-1")
    assert payload["cpu_percent"] == 0.0
    assert payload["ram_total_mb"] == 0.0
    assert payload["idempotency_key"] == "resilient-key-1"
