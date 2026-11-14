"""
ServicePulse Native Windows Agent - Telemetry Aggregator
Packages real host metrics into backend-compatible idempotent telemetry payloads.
Author: Muhammadyusuf Usmonov (AT-Servis BMI)
"""
import datetime
import uuid
from typing import Any, Dict, Optional

from servicepulse.collectors.defender import DefenderCollector
from servicepulse.collectors.system import SystemCollector
from servicepulse.collectors.windows_activation import WindowsActivationCollector
from servicepulse.logging.setup import get_logger

logger = get_logger()


class TelemetryAggregator:
    """Consolidates metrics from all system collectors into an API payload."""

    @classmethod
    def collect_payload(cls, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers system, activation, and defender metrics with error resilience.
        Returns a dictionary adhering to backend AgentTelemetryRequest schema.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        idemp = idempotency_key or f"tx_{uuid.uuid4().hex}"

        # 1. System Metrics
        try:
            sys_metrics = SystemCollector.collect_all()
            cpu_pct = sys_metrics.cpu.cpu_percent
            ram_pct = sys_metrics.ram.ram_percent
            ram_used = sys_metrics.ram.ram_used_mb
            ram_total = sys_metrics.ram.ram_total_mb
            disk_pct = sys_metrics.disk.disk_percent
            disk_used = sys_metrics.disk.disk_used_gb
            disk_total = sys_metrics.disk.disk_total_gb
        except Exception as e:
            logger.warning(f"Error gathering system metrics for telemetry payload: {e}")
            cpu_pct = 0.0
            ram_pct = 0.0
            ram_used = 0.0
            ram_total = 0.0
            disk_pct = 0.0
            disk_used = 0.0
            disk_total = 0.0

        # 2. Windows Activation Status
        try:
            act = WindowsActivationCollector.collect(timeout_seconds=5)
            activation_status = act.status
        except Exception as e:
            logger.warning(f"Error gathering activation status: {e}")
            activation_status = "unavailable"

        # 3. Windows Defender Status
        try:
            def_stat = DefenderCollector.collect(timeout_seconds=5)
            defender_status = def_stat.status
        except Exception as e:
            logger.warning(f"Error gathering Defender status: {e}")
            defender_status = "unavailable"

        payload = {
            "cpu_percent": float(cpu_pct),
            "ram_percent": float(ram_pct),
            "ram_used_mb": float(ram_used),
            "ram_total_mb": float(ram_total),
            "disk_percent": float(disk_pct),
            "disk_used_gb": float(disk_used),
            "disk_total_gb": float(disk_total),
            "windows_activation_status": activation_status[:50] if activation_status else None,
            "windows_defender_status": defender_status[:50] if defender_status else None,
            "recorded_at": now.isoformat(),
            "idempotency_key": idemp,
        }
        return payload
