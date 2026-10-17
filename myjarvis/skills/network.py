"""
MyJarvis — Network Skill
Ping, speedtest, interfaces, DNS, connections
"""
from __future__ import annotations

import logging
import socket
import subprocess
import psutil
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class NetworkSkill(Skill):
    """Network diagnostics: ping, speedtest, interfaces, DNS, connections."""

    name = "network"
    description = "Network: ping, speedtest, interfaces, DNS, connections, bandwidth"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()

    def _register_actions(self) -> None:
        self.register_action("ping", self.ping)
        self.register_action("speedtest", self.speedtest)
        self.register_action("interfaces", self.list_interfaces)
        self.register_action("connections", self.list_connections)
        self.register_action("dns", self.dns_lookup)
        self.register_action("traceroute", self.traceroute)
        self.register_action("port", self.check_port)
        self.register_action("bandwidth", self.bandwidth_usage)

    def ping(self, host: str = "8.8.8.8", count: int = 4, timeout: int = 5) -> Dict[str, Any]:
        """Ping a host."""
        try:
            import platform
            system = platform.system().lower()

            if system == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 5)

            # Parse output
            output = result.stdout
            stats = {"host": host, "sent": count, "received": 0, "lost": 0, "min_ms": 0, "max_ms": 0, "avg_ms": 0}

            if result.returncode == 0:
                stats["received"] = count
                # Parse times (simplified)
                import re
                times = re.findall(r"time[=<](\d+\.?\d*)\s*ms", output)
                if times:
                    times = [float(t) for t in times]
                    stats["min_ms"] = min(times)
                    stats["max_ms"] = max(times)
                    stats["avg_ms"] = sum(times) / len(times)
            else:
                stats["lost"] = count

            return {"success": result.returncode == 0, "stats": stats, "raw": output}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ping timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def speedtest(self, server: str = "") -> Dict[str, Any]:
        """Run speedtest (requires speedtest-cli)."""
        try:
            cmd = ["speedtest-cli", "--json"]
            if server:
                cmd.extend(["--server", server])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            import json
            data = json.loads(result.stdout)
            return {
                "success": True,
                "download_mbps": data.get("download", 0) / 1_000_000,
                "upload_mbps": data.get("upload", 0) / 1_000_000,
                "ping_ms": data.get("ping", 0),
                "server": data.get("server", {}),
            }

        except FileNotFoundError:
            return {"success": False, "error": "speedtest-cli not installed: pip install speedtest-cli"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_interfaces(self) -> Dict[str, Any]:
        """List network interfaces with stats."""
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            io = psutil.net_io_counters(pernic=True)

            result = []
            for name, addrs in interfaces.items():
                iface = {
                    "name": name,
                    "is_up": stats.get(name, {}).isup if name in stats else False,
                    "speed": stats.get(name, {}).speed if name in stats else 0,
                    "mtu": stats.get(name, {}).mtu if name in stats else 0,
                    "addresses": [],
                    "bytes_sent": io.get(name, {}).bytes_sent if name in io else 0,
                    "bytes_recv": io.get(name, {}).bytes_recv if name in io else 0,
                }
                for addr in addrs:
                    iface["addresses"].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    })
                result.append(iface)

            return {"success": True, "interfaces": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_connections(self, kind: str = "inet") -> Dict[str, Any]:
        """List network connections."""
        try:
            conns = psutil.net_connections(kind=kind)
            result = []
            for c in conns:
                result.append({
                    "fd": c.fd,
                    "family": str(c.family),
                    "type": str(c.type),
                    "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                    "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                    "status": c.status,
                    "pid": c.pid,
                })
            return {"success": True, "connections": result, "count": len(result)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def dns_lookup(self, domain: str, record_type: str = "A") -> Dict[str, Any]:
        """DNS lookup."""
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, record_type)
            records = [str(r) for r in answers]
            return {"success": True, "domain": domain, "type": record_type, "records": records}
        except ImportError:
            return {"success": False, "error": "dnspython not installed: pip install dnspython"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def traceroute(self, host: str, max_hops: int = 30) -> Dict[str, Any]:
        """Traceroute to host."""
        try:
            import platform
            system = platform.system().lower()
            if system == "windows":
                cmd = ["tracert", "-h", str(max_hops), host]
            else:
                cmd = ["traceroute", "-m", str(max_hops), host]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {"success": result.returncode == 0, "output": result.stdout, "host": host}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_port(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Check if TCP port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return {"success": True, "host": host, "port": port, "open": result == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def bandwidth_usage(self, interface: str = "", interval: int = 1) -> Dict[str, Any]:
        """Get bandwidth usage per interface."""
        try:
            before = psutil.net_io_counters(pernic=True)
            import time
            time.sleep(interval)
            after = psutil.net_io_counters(pernic=True)

            result = {}
            for name in after:
                if interface and name != interface:
                    continue
                b = before.get(name)
                a = after[name]
                if b:
                    result[name] = {
                        "bytes_sent_per_sec": (a.bytes_sent - b.bytes_sent) / interval,
                        "bytes_recv_per_sec": (a.bytes_recv - b.bytes_recv) / interval,
                        "packets_sent_per_sec": (a.packets_sent - b.packets_sent) / interval,
                        "packets_recv_per_sec": (a.packets_recv - b.packets_recv) / interval,
                    }
            return {"success": True, "bandwidth": result}
        except Exception as e:
            return {"success": False, "error": str(e)}