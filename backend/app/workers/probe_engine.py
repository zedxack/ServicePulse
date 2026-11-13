"""
ServicePulse - Network Monitoring Probe Engine
High-performance asynchronous ICMP ping & TCP port connectivity probes.
Safe non-privileged socket/process execution with deterministic simulation adapter.
Author: Muhammadyusuf Usmonov
"""
import asyncio
import platform
import re
import socket
import time
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.logging import logger
from backend.app.schemas.monitoring import ProbeResult


class ProbeEngine:
    """
    Asynchronous network probe engine.
    Supports ICMP ping (non-privileged safe fallback) and TCP port checks.
    Includes a deterministic simulation adapter for demo devices.
    """

    # Global simulation override hook (used by tests to simulate failure / recovery scenarios)
    _simulation_override: Optional[bool] = None

    @classmethod
    def set_simulation_override(cls, override: Optional[bool]) -> None:
        """Allows tests to force simulated probes to return True or False."""
        cls._simulation_override = override

    @staticmethod
    async def probe_device(
        device_id: int,
        ip_address: str,
        check_type: str = "icmp_ping",
        port: Optional[int] = None,
        timeout_seconds: float = 3.0,
        use_simulation: bool = False,
    ) -> ProbeResult:
        """
        Execute an authorized network probe against target IP.
        Never scans arbitrary subnets; target must be explicitly provided.
        """
        now = datetime.now(timezone.utc)

        # 1. Check if simulation adapter should handle this probe
        if use_simulation or ProbeEngine._simulation_override is not None:
            return await ProbeEngine._run_simulation(device_id, ip_address, check_type, port, now)

        # 2. Execute real probe
        if check_type == "icmp_ping":
            return await ProbeEngine.ping_ip(device_id, ip_address, timeout_seconds, now)
        elif check_type == "tcp_port":
            if not port:
                port = 80
            return await ProbeEngine.check_tcp_port(device_id, ip_address, port, timeout_seconds, now)
        else:
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type=check_type,
                port=port,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"Unsupported check type: {check_type}",
                is_simulated=False,
                checked_at=now,
            )

    @staticmethod
    async def ping_ip(device_id: int, ip_address: str, timeout_seconds: float, checked_at: datetime) -> ProbeResult:
        """
        Safe non-privileged ICMP ping.
        Uses OS standard ping utility in a child process to avoid requiring raw socket privileges.
        """
        is_windows = platform.system().lower() == "windows"
        t_start = time.perf_counter()

        if is_windows:
            timeout_ms = int(timeout_seconds * 1000)
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip_address]
        else:
            timeout_sec = max(1, int(timeout_seconds))
            cmd = ["ping", "-c", "1", "-W", str(timeout_sec), ip_address]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds + 1.0)
            duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            stdout_str = stdout.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                # Extract latency if available
                latency_ms = ProbeEngine._extract_ping_latency(stdout_str, duration_ms)
                return ProbeResult(
                    device_id=device_id,
                    target_ip=ip_address,
                    check_type="icmp_ping",
                    port=None,
                    is_successful=True,
                    response_time_ms=latency_ms,
                    packet_loss_percent=0.0,
                    error_message=None,
                    is_simulated=False,
                    checked_at=checked_at,
                )
            else:
                return ProbeResult(
                    device_id=device_id,
                    target_ip=ip_address,
                    check_type="icmp_ping",
                    port=None,
                    is_successful=False,
                    response_time_ms=0.0,
                    packet_loss_percent=100.0,
                    error_message="Host unreachable or ping request timed out",
                    is_simulated=False,
                    checked_at=checked_at,
                )

        except (asyncio.TimeoutError, TimeoutError):
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="icmp_ping",
                port=None,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"Ping timed out after {timeout_seconds}s",
                is_simulated=False,
                checked_at=checked_at,
            )
        except Exception as exc:
            logger.warning("Subprocess ping execution error for %s: %s", ip_address, str(exc))
            # Fallback to TCP ping on port 80 or 443 if ping binary is restricted
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="icmp_ping",
                port=None,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"Ping failed: {str(exc)}",
                is_simulated=False,
                checked_at=checked_at,
            )

    @staticmethod
    async def check_tcp_port(
        device_id: int,
        ip_address: str,
        port: int,
        timeout_seconds: float,
        checked_at: datetime
    ) -> ProbeResult:
        """
        Asynchronous TCP 3-way handshake verification.
        Measures connect latency in milliseconds.
        Clearly notes that TCP port connectivity confirms socket accessibility, not app-level health.
        """
        t_start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_address, port),
                timeout=timeout_seconds,
            )
            duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="tcp_port",
                port=port,
                is_successful=True,
                response_time_ms=duration_ms,
                packet_loss_percent=0.0,
                error_message=None,
                is_simulated=False,
                checked_at=checked_at,
            )
        except asyncio.TimeoutError:
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="tcp_port",
                port=port,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"TCP connection to port {port} timed out after {timeout_seconds}s",
                is_simulated=False,
                checked_at=checked_at,
            )
        except (ConnectionRefusedError, socket.error) as e:
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="tcp_port",
                port=port,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"Connection refused on port {port}: {str(e)}",
                is_simulated=False,
                checked_at=checked_at,
            )
        except Exception as e:
            return ProbeResult(
                device_id=device_id,
                target_ip=ip_address,
                check_type="tcp_port",
                port=port,
                is_successful=False,
                response_time_ms=0.0,
                packet_loss_percent=100.0,
                error_message=f"TCP probe error: {str(e)}",
                is_simulated=False,
                checked_at=checked_at,
            )

    @staticmethod
    async def _run_simulation(
        device_id: int,
        ip_address: str,
        check_type: str,
        port: Optional[int],
        checked_at: datetime
    ) -> ProbeResult:
        """
        Deterministic simulation adapter for sample/demo devices.
        Prevents outbound network spam to demonstration lab IP ranges (e.g. 192.168.10.x).
        Results are explicitly marked is_simulated=True.
        """
        # Yield to event loop
        await asyncio.sleep(0.01)

        # Respect test override if set
        if ProbeEngine._simulation_override is not None:
            success = ProbeEngine._simulation_override
        else:
            # By default, sample devices are healthy unless specified
            success = True

        latency = 2.4 if success else 0.0
        error_msg = None if success else "Simulated network timeout (Host unreachable)"

        return ProbeResult(
            device_id=device_id,
            target_ip=ip_address,
            check_type=check_type,
            port=port,
            is_successful=success,
            response_time_ms=latency,
            packet_loss_percent=0.0 if success else 100.0,
            error_message=error_msg,
            is_simulated=True,
            checked_at=checked_at,
        )

    @staticmethod
    def _extract_ping_latency(stdout_text: str, fallback_ms: float) -> float:
        """Extract RTT from ping stdout output across Linux and Windows formats."""
        # Windows: "time=2ms" or "time<1ms"
        win_match = re.search(r"time[=<](\d+)ms", stdout_text, re.IGNORECASE)
        if win_match:
            return float(win_match.group(1))

        # Linux: "time=2.45 ms"
        linux_match = re.search(r"time=(\d+(?:\.\d+)?)\s*ms", stdout_text, re.IGNORECASE)
        if linux_match:
            return float(linux_match.group(1))

        return fallback_ms
