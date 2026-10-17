"""
MyJarvis — Process Skill
List, monitor, manage processes
"""
from __future__ import annotations

import logging
import psutil
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class ProcessSkill(Skill):
    """Process management: list, kill, monitor, priority."""

    name = "process"
    description = "Processes: list, kill, monitor CPU/memory, priority, startup"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()

    def _register_actions(self) -> None:
        self.register_action("list", self.list_processes)
        self.register_action("kill", self.kill_process)
        self.register_action("info", self.process_info)
        self.register_action("cpu", self.cpu_usage)
        self.register_action("memory", self.memory_usage)
        self.register_action("tree", self.process_tree)
        self.register_action("priority", self.set_priority)
        self.register_action("wait", self.wait_for_exit)

    def list_processes(
        self,
        filter_name: str = "",
        sort: str = "cpu",
        limit: int = 50,
        user_only: bool = True,
    ) -> Dict[str, Any]:
        """List running processes."""
        try:
            current_user = psutil.Process().username() if user_only else None
            processes = []

            for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "status", "create_time"]):
                try:
                    info = proc.info
                    if user_only and info["username"] != current_user:
                        continue
                    if filter_name and filter_name.lower() not in info["name"].lower():
                        continue

                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "username": info["username"],
                        "cpu_percent": info["cpu_percent"],
                        "memory_percent": info["memory_percent"],
                        "status": info["status"],
                        "create_time": info["create_time"],
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if sort == "cpu":
                processes.sort(key=lambda x: x["cpu_percent"] or 0, reverse=True)
            elif sort == "memory":
                processes.sort(key=lambda x: x["memory_percent"] or 0, reverse=True)
            elif sort == "pid":
                processes.sort(key=lambda x: x["pid"])
            elif sort == "name":
                processes.sort(key=lambda x: x["name"].lower())

            return {"success": True, "processes": processes[:limit], "count": len(processes)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def kill_process(self, pid: int = None, name: str = "", force: bool = False) -> Dict[str, Any]:
        """Kill process by PID or name."""
        try:
            killed = []
            if pid:
                try:
                    proc = psutil.Process(pid)
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    proc.wait(timeout=5)
                    killed.append({"pid": pid, "name": proc.name()})
                except psutil.NoSuchProcess:
                    return {"success": False, "error": f"Process {pid} not found"}
                except psutil.AccessDenied:
                    return {"success": False, "error": f"Access denied killing {pid}"}

            if name:
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if name.lower() in proc.info["name"].lower():
                            if force:
                                proc.kill()
                            else:
                                proc.terminate()
                            proc.wait(timeout=5)
                            killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            return {"success": True, "killed": killed, "count": len(killed)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed process information."""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                info = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "exe": proc.exe(),
                    "cmdline": proc.cmdline(),
                    "cwd": proc.cwd(),
                    "username": proc.username(),
                    "status": proc.status(),
                    "create_time": proc.create_time(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_info": proc.memory_info()._asdict(),
                    "num_threads": proc.num_threads(),
                    "open_files": [f.path for f in proc.open_files()] if proc.open_files() else [],
                    "connections": [c._asdict() for c in proc.connections()] if proc.connections() else [],
                    "children": [c.pid for c in proc.children(recursive=True)],
                    "parent": proc.ppid(),
                }
            return {"success": True, "info": info}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cpu_usage(self, interval: float = 1.0, per_cpu: bool = False) -> Dict[str, Any]:
        """Get CPU usage."""
        try:
            total = psutil.cpu_percent(interval=interval)
            result = {"total_percent": total}
            if per_cpu:
                result["per_cpu"] = psutil.cpu_percent(interval=interval, percpu=True)
            result["count_logical"] = psutil.cpu_count(logical=True)
            result["count_physical"] = psutil.cpu_count(logical=False)
            result["freq"] = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            return {"success": True, "cpu": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def memory_usage(self) -> Dict[str, Any]:
        """Get memory usage."""
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "success": True,
                "memory": {
                    "total": vm.total,
                    "available": vm.available,
                    "used": vm.used,
                    "free": vm.free,
                    "percent": vm.percent,
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_tree(self, pid: int = None) -> Dict[str, Any]:
        """Get process tree."""
        try:
            if pid is None:
                pid = psutil.Process().pid

            def build_tree(p):
                try:
                    proc = psutil.Process(p)
                    children = []
                    for child in proc.children():
                        children.append(build_tree(child.pid))
                    return {
                        "pid": proc.pid,
                        "name": proc.name(),
                        "cpu_percent": proc.cpu_percent(),
                        "memory_percent": proc.memory_percent(),
                        "children": children,
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {"pid": p, "name": "unknown", "children": []}

            return {"success": True, "tree": build_tree(pid)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_priority(self, pid: int, priority: str) -> Dict[str, Any]:
        """Set process priority: low, below_normal, normal, above_normal, high, realtime."""
        priorities = {
            "low": psutil.IDLE_PRIORITY_CLASS,
            "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
            "normal": psutil.NORMAL_PRIORITY_CLASS,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
            "high": psutil.HIGH_PRIORITY_CLASS,
            "realtime": psutil.REALTIME_PRIORITY_CLASS,
        }

        if priority not in priorities:
            return {"success": False, "error": f"Invalid priority. Valid: {list(priorities.keys())}"}

        try:
            proc = psutil.Process(pid)
            proc.nice(priorities[priority])
            return {"success": True, "pid": pid, "priority": priority}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied (try as admin)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def wait_for_exit(self, pid: int, timeout: int = 0) -> Dict[str, Any]:
        """Wait for process to exit."""
        try:
            proc = psutil.Process(pid)
            return_code = proc.wait(timeout=timeout if timeout > 0 else None)
            return {"success": True, "pid": pid, "return_code": return_code}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}