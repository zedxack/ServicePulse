"""
ServicePulse Native Windows Agent - Network Telemetry Collector
Collects local IPv4 addresses, active interface states, and hardware MAC addresses.
Author: Muhammadyusuf Usmonov
"""
import socket
from typing import List, Optional

import psutil
from pydantic import BaseModel, Field

from servicepulse.logging.setup import get_logger

logger = get_logger()


class NetworkInterfaceInfo(BaseModel):
    name: str
    is_up: bool
    speed_mbps: Optional[int] = None
    ipv4_addresses: List[str] = Field(default_factory=list)
    mac_address: Optional[str] = None


class NetworkInfo(BaseModel):
    primary_ip: str
    hostname: str
    interfaces: List[NetworkInterfaceInfo] = Field(default_factory=list)


class NetworkCollector:
    """Collects network interfaces, addresses, and connectivity states."""

    @staticmethod
    def get_primary_ip() -> str:
        """
        Determine the primary local IPv4 address using a dummy UDP socket.
        Does not actually transmit network packets.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to non-routable address to determine outbound routing interface
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    @classmethod
    def collect(cls) -> NetworkInfo:
        """Collect network status across all interfaces."""
        hostname = socket.gethostname()
        primary_ip = cls.get_primary_ip()
        interfaces_list: List[NetworkInterfaceInfo] = []

        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, addr_list in addrs.items():
                is_up = False
                speed = None
                if iface_name in stats:
                    is_up = stats[iface_name].isup
                    speed = stats[iface_name].speed

                ipv4s = []
                mac = None

                for a in addr_list:
                    if a.family == socket.AF_INET:
                        ipv4s.append(a.address)
                    elif hasattr(psutil, "AF_LINK") and a.family == psutil.AF_LINK:
                        if a.address and a.address.strip():
                            mac = a.address.strip()

                # If MAC address format looks valid (contains colons or dashes)
                if not mac:
                    for a in addr_list:
                        if a.address and ("-" in a.address or ":" in a.address) and len(a.address) == 17:
                            mac = a.address

                # Skip virtual loopback if other interfaces exist
                if iface_name.lower().startswith("loopback") and len(addrs) > 1:
                    continue

                interfaces_list.append(NetworkInterfaceInfo(
                    name=iface_name,
                    is_up=is_up,
                    speed_mbps=speed if speed and speed > 0 else None,
                    ipv4_addresses=ipv4s,
                    mac_address=mac,
                ))

        except Exception as e:
            logger.warning(f"Error collecting network interface information: {e}")

        return NetworkInfo(
            primary_ip=primary_ip,
            hostname=hostname,
            interfaces=interfaces_list,
        )
