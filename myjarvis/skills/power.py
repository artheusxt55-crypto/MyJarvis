"""
MyJarvis — Power Skill
Sleep, hibernate, shutdown, battery, power plans
"""
from __future__ import annotations

import logging
import subprocess
import platform
from typing import Any, Dict

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class PowerSkill(Skill):
    """Power management: sleep, hibernate, shutdown, battery, power plans."""

    name = "power"
    description = "Power: sleep, hibernate, shutdown, restart, battery, power plans"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._is_windows = platform.system() == "Windows"

    def _register_actions(self) -> None:
        self.register_action("sleep", self.sleep)
        self.register_action("hibernate", self.hibernate)
        self.register_action("shutdown", self.shutdown)
        self.register_action("restart", self.restart)
        self.register_action("lock", self.lock)
        self.register_action("battery", self.battery_status)
        self.register_action("plan", self.power_plan)
        self.register_action("timeout", self.set_timeout)

    def sleep(self, hybrid: bool = False) -> Dict[str, Any]:
        """Sleep (suspend). hybrid=True = hybrid sleep."""
        try:
            if self._is_windows:
                if hybrid:
                    subprocess.run(
                        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                        check=True
                    )
                else:
                    subprocess.run(
                        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                        check=True
                    )
            else:
                subprocess.run(["systemctl", "suspend"], check=True)
            return {"success": True, "action": "sleep", "hybrid": hybrid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hibernate(self) -> Dict[str, Any]:
        """Hibernate."""
        try:
            if self._is_windows:
                subprocess.run(["shutdown", "/h"], check=True)
            else:
                subprocess.run(["systemctl", "hibernate"], check=True)
            return {"success": True, "action": "hibernate"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self, delay: int = 0, force: bool = False) -> Dict[str, Any]:
        """Shutdown."""
        try:
            if self._is_windows:
                cmd = ["shutdown", "/s", "/t", str(delay)]
                if force:
                    cmd.append("/f")
                subprocess.run(cmd, check=True)
            else:
                cmd = ["shutdown", "-h", f"+{delay//60}" if delay else "now"]
                if force:
                    cmd.insert(1, "-f")
                subprocess.run(cmd, check=True)
            return {"success": True, "action": "shutdown", "delay": delay}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart(self, delay: int = 0, force: bool = False) -> Dict[str, Any]:
        """Restart."""
        try:
            if self._is_windows:
                cmd = ["shutdown", "/r", "/t", str(delay)]
                if force:
                    cmd.append("/f")
                subprocess.run(cmd, check=True)
            else:
                cmd = ["shutdown", "-r", f"+{delay//60}" if delay else "now"]
                if force:
                    cmd.insert(1, "-f")
                subprocess.run(cmd, check=True)
            return {"success": True, "action": "restart", "delay": delay}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def lock(self) -> Dict[str, Any]:
        """Lock workstation."""
        try:
            if self._is_windows:
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            else:
                subprocess.run(["loginctl", "lock-session"], check=True)
            return {"success": True, "action": "lock"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def battery_status(self) -> Dict[str, Any]:
        """Get battery status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if not battery:
                return {"success": False, "error": "No battery found"}

            return {
                "success": True,
                "battery": {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def power_plan(self, action: str = "list", plan: str = "") -> Dict[str, Any]:
        """Manage power plans: list, get, set, import, export."""
        if not self._is_windows:
            return {"success": False, "error": "Power plans only on Windows"}

        try:
            if action == "list":
                result = subprocess.run(
                    ["powercfg", "/list"],
                    capture_output=True, text=True, check=True
                )
                plans = []
                for line in result.stdout.strip().split("\n"):
                    if "GUID" in line:
                        parts = line.split()
                        guid = parts[parts.index("GUID") + 1] if "GUID" in parts else ""
                        name = " ".join(parts[3:]) if len(parts) > 3 else ""
                        plans.append({"guid": guid, "name": name.strip("* ")})
                return {"success": True, "plans": plans}

            elif action == "get":
                result = subprocess.run(
                    ["powercfg", "/getactivescheme"],
                    capture_output=True, text=True, check=True
                )
                guid = result.stdout.strip().split()[-1]
                return {"success": True, "active_guid": guid}

            elif action == "set":
                if not plan:
                    return {"success": False, "error": "Plan GUID required"}
                subprocess.run(["powercfg", "/setactive", plan], check=True)
                return {"success": True, "set": plan}

            elif action == "import":
                if not plan:
                    return {"success": False, "error": "File path required"}
                result = subprocess.run(
                    ["powercfg", "/import", plan],
                    capture_output=True, text=True, check=True
                )
                return {"success": True, "imported": result.stdout.strip()}

            elif action == "export":
                if not plan:
                    return {"success": False, "error": "Plan GUID and file path required"}
                # plan = "guid path"
                parts = plan.split()
                if len(parts) != 2:
                    return {"success": False, "error": "Usage: plan='GUID path'"}
                subprocess.run(["powercfg", "/export", parts[1], parts[0]], check=True)
                return {"success": True, "exported": parts[1]}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_timeout(self, ac_minutes: int = None, dc_minutes: int = None) -> Dict[str, Any]:
        """Set display/sleep timeouts (minutes)."""
        if not self._is_windows:
            return {"success": False, "error": "Windows only"}

        try:
            active = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True, text=True, check=True
            ).stdout.strip().split()[-1]

            if ac_minutes is not None:
                subprocess.run(
                    ["powercfg", "/change", active, "/monitor-timeout-ac", str(ac_minutes)],
                    check=True
                )
                subprocess.run(
                    ["powercfg", "/change", active, "/standby-timeout-ac", str(ac_minutes)],
                    check=True
                )

            if dc_minutes is not None:
                subprocess.run(
                    ["powercfg", "/change", active, "/monitor-timeout-dc", str(dc_minutes)],
                    check=True
                )
                subprocess.run(
                    ["powercfg", "/change", active, "/standby-timeout-dc", str(dc_minutes)],
                    check=True
                )

            return {"success": True, "ac_minutes": ac_minutes, "dc_minutes": dc_minutes}
        except Exception as e:
            return {"success": False, "error": str(e)}