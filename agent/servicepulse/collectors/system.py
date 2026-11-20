"""
ServicePulse Native Windows Agent - System Telemetry Collector
Gathers genuine CPU, Memory, Disk, and Operating System metrics using psutil and Windows APIs.
Author: Muhammadyusuf Usmonov
"""
import os
import platform
import socket
import time
from typing import Any, Dict, List, Optional

import psutil
from pydantic import BaseModel, Field

from servicepulse.logging.setup import get_logger

logger = get_logger()


class CpuMetrics(BaseModel):
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    core_count_logical: int
    core_count_physical: Optional[int] = None
    frequency_mhz: Optional[float] = None


class RamMetrics(BaseModel):
    ram_percent: float = Field(..., ge=0.0, le=100.0)
    ram_used_mb: float = Field(..., ge=0.0)
    ram_total_mb: float = Field(..., ge=0.0)
    ram_available_mb: float = Field(..., ge=0.0)


class DiskMetrics(BaseModel):
    disk_percent: float = Field(..., ge=0.0, le=100.0)
    disk_used_gb: float = Field(..., ge=0.0)
    disk_total_gb: float = Field(..., ge=0.0)
    disk_free_gb: float = Field(..., ge=0.0)
    drives: List[Dict[str, Any]] = Field(default_factory=list)


class OsMetrics(BaseModel):
    hostname: str
    os_name: str
    os_edition: Optional[str] = None
    os_version: str
    build_number: Optional[str] = None
    architecture: str
    boot_time_utc: float
    uptime_seconds: float


class SystemMetrics(BaseModel):
    cpu: CpuMetrics
    ram: RamMetrics
    disk: DiskMetrics
    os: OsMetrics


class SystemCollector:
    """Collects real hardware and OS telemetry from the host machine."""

    @staticmethod
    def collect_cpu() -> CpuMetrics:
        """Collect current CPU utilization and topology."""
        try:
            percent = float(psutil.cpu_percent(interval=0.1))
            logical = psutil.cpu_count(logical=True) or 1
            physical = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            freq_mhz = float(freq.current) if freq and freq.current else None

            return CpuMetrics(
                cpu_percent=percent,
                core_count_logical=logical,
                core_count_physical=physical,
                frequency_mhz=freq_mhz,
            )
        except Exception as e:
            logger.warning(f"Error collecting CPU metrics: {e}")
            return CpuMetrics(cpu_percent=0.0, core_count_logical=1)

    @staticmethod
    def collect_ram() -> RamMetrics:
        """Collect RAM usage and capacities in Megabytes."""
        try:
            vm = psutil.virtual_memory()
            total_mb = round(vm.total / (1024 * 1024), 2)
            used_mb = round(vm.used / (1024 * 1024), 2)
            avail_mb = round(vm.available / (1024 * 1024), 2)
            percent = float(vm.percent)

            return RamMetrics(
                ram_percent=percent,
                ram_used_mb=used_mb,
                ram_total_mb=total_mb,
                ram_available_mb=avail_mb,
            )
        except Exception as e:
            logger.warning(f"Error collecting RAM metrics: {e}")
            return RamMetrics(ram_percent=0.0, ram_used_mb=0.0, ram_total_mb=0.0, ram_available_mb=0.0)

    @staticmethod
    def collect_disk() -> DiskMetrics:
        """
        Collect fixed disk partition usage in Gigabytes.
        Ignores removable media, CD-ROMs, and inaccessible virtual mounts.
        """
        total_bytes = 0
        used_bytes = 0
        free_bytes = 0
        drives_info = []

        try:
            partitions = psutil.disk_partitions(all=False)
            seen_mounts = set()

            for part in partitions:
                # Filter out cdrom, floppy, network drives or inaccessible
                if "cdrom" in part.opts or part.fstype == "" or part.mountpoint in seen_mounts:
                    continue

                # On Windows, drive letters like C:\, D:\
                if os.name == "nt" and "fixed" not in part.opts and not part.mountpoint.endswith(":\\"):
                    # Check drive type
                    pass

                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    seen_mounts.add(part.mountpoint)
                    total_bytes += usage.total
                    used_bytes += usage.used
                    free_bytes += usage.free

                    drives_info.append({
                        "mountpoint": part.mountpoint,
                        "device": part.device,
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "free_gb": round(usage.free / (1024 ** 3), 2),
                        "percent": float(usage.percent),
                    })
                except (PermissionError, OSError) as pe:
                    logger.debug(f"Skipping partition {part.mountpoint}: {pe}")
                    continue

            # Fallback if no fixed drive was parsed
            if not drives_info:
                # Try default primary drive root
                root_path = "C:\\" if os.name == "nt" else "/"
                usage = psutil.disk_usage(root_path)
                total_bytes = usage.total
                used_bytes = usage.used
                free_bytes = usage.free
                drives_info.append({
                    "mountpoint": root_path,
                    "device": root_path,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "percent": float(usage.percent),
                })

            total_gb = round(total_bytes / (1024 ** 3), 2)
            used_gb = round(used_bytes / (1024 ** 3), 2)
            free_gb = round(free_bytes / (1024 ** 3), 2)
            overall_percent = round((used_bytes / total_bytes * 100), 2) if total_bytes > 0 else 0.0

            return DiskMetrics(
                disk_percent=overall_percent,
                disk_used_gb=used_gb,
                disk_total_gb=total_gb,
                disk_free_gb=free_gb,
                drives=drives_info,
            )
        except Exception as e:
            logger.warning(f"Error collecting Disk metrics: {e}")
            return DiskMetrics(disk_percent=0.0, disk_used_gb=0.0, disk_total_gb=0.0, disk_free_gb=0.0)

    @staticmethod
    def collect_os() -> OsMetrics:
        """Collect host operating system details and uptime."""
        try:
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            hostname = socket.gethostname()
            system_name = platform.system()
            release = platform.release()
            version = platform.version()
            arch = platform.machine() or "x64"

            # Check Windows edition if possible
            edition = None
            if os.name == "nt":
                try:
                    edition = platform.win32_edition()
                except Exception:
                    edition = f"{system_name} {release}"

            os_name_full = f"{system_name} {release}".strip()

            return OsMetrics(
                hostname=hostname,
                os_name=os_name_full,
                os_edition=edition,
                os_version=version,
                build_number=version.split(".")[-1] if "." in version else version,
                architecture=arch,
                boot_time_utc=boot_time,
                uptime_seconds=round(uptime, 2),
            )
        except Exception as e:
            logger.warning(f"Error collecting OS metrics: {e}")
            return OsMetrics(
                hostname="unknown",
                os_name="Windows",
                os_version="10.0",
                architecture="x64",
                boot_time_utc=0.0,
                uptime_seconds=0.0,
            )

    @classmethod
    def collect_all(cls) -> SystemMetrics:
        """Collect complete consolidated system metrics."""
        return SystemMetrics(
            cpu=cls.collect_cpu(),
            ram=cls.collect_ram(),
            disk=cls.collect_disk(),
            os=cls.collect_os(),
        )
