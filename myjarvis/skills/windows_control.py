"""
MyJarvis — Windows Control Skill
Controls windows, apps, system settings on Windows
"""
from __future__ import annotations

import subprocess
import logging
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class WindowsControlSkill(Skill):
    """Windows system control: apps, windows, settings, shortcuts."""

    name = "windows_control"
    description = "Control Windows: launch apps, manage windows, system settings, shortcuts"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()

    def _register_actions(self) -> None:
        self.register_action("launch", self.launch_app)
        self.register_action("close", self.close_app)
        self.register_action("list_windows", self.list_windows)
        self.register_action("focus", self.focus_window)
        self.register_action("minimize", self.minimize_window)
        self.register_action("maximize", self.maximize_window)
        self.register_action("screenshot", self.take_screenshot)
        self.register_action("run_command", self.run_command)
        self.register_action("shortcut", self.send_shortcut)
        self.register_action("volume", self.set_volume)
        self.register_action("brightness", self.set_brightness)
        self.register_action("power", self.power_action)
        self.register_action("startup", self.manage_startup)

    # --- App Management ---

    def launch_app(self, app: str, args: str = "", wait: bool = False) -> Dict[str, Any]:
        """Launch a Windows application."""
        try:
            # Try direct executable first
            if app.endswith(".exe") or "\\" in app or "/" in app:
                cmd = [app] + (args.split() if args else [])
            else:
                # Try via start command for registered apps
                cmd = ["start", "", app] + (args.split() if args else [])

            if wait:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
            else:
                subprocess.Popen(cmd, shell=True)
                return {"success": True, "message": f"Launched {app}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_app(self, app: str, force: bool = False) -> Dict[str, Any]:
        """Close a Windows application by name or PID."""
        try:
            if force:
                cmd = ["taskkill", "/F", "/IM", app]
            else:
                cmd = ["taskkill", "/IM", app]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Window Management ---

    def list_windows(self, filter_title: str = "") -> Dict[str, Any]:
        """List open windows using PowerShell."""
        try:
            ps_script = """
            Add-Type @'
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {
                [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
                [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
                [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
                [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
                [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
                public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            }
'@
            $windows = @()
            $callback = [Win32+EnumWindowsProc] {
                param($hWnd, $lParam)
                if ([Win32]::IsWindowVisible($hWnd)) {
                    $len = [Win32]::GetWindowTextLength($hWnd)
                    if ($len -gt 0) {
                        $sb = New-Object System.Text.StringBuilder($len + 1)
                        [Win32]::GetWindowText($hWnd, $sb, $sb.Capacity) | Out-Null
                        $title = $sb.ToString()
                        $pid = 0
                        [Win32]::GetWindowThreadProcessId($hWnd, [ref]$pid) | Out-Null
                        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                        $windows += [PSCustomObject]@{
                            Handle = $hWnd
                            Title = $title
                            ProcessId = $pid
                            ProcessName = $proc.ProcessName
                            MainWindowTitle = $proc.MainWindowTitle
                        }
                    }
                }
                return $true
            }
            [Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
            $windows | Where-Object { $_.Title -ne "" } | Select-Object Handle, Title, ProcessId, ProcessName | ConvertTo-Json -Depth 3
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                import json
                windows = json.loads(result.stdout)
                if filter_title:
                    windows = [w for w in windows if filter_title.lower() in w["Title"].lower()]
                return {"success": True, "windows": windows}
            return {"success": True, "windows": []}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def focus_window(self, title: str = "", handle: int = 0) -> Dict[str, Any]:
        """Bring window to front by title or handle."""
        try:
            if handle:
                ps_script = f"""
                Add-Type @'
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                }}
'@
                [Win32]::ShowWindow([IntPtr]::new({handle}), 9) | Out-Null
                [Win32]::SetForegroundWindow([IntPtr]::new({handle})) | Out-Null
                """
            else:
                ps_script = f"""
                Add-Type @'
                using System;
                using System.Runtime.InteropServices;
                public class Win32 {{
                    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
                    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
                    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
                    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
                }}
'@
                $found = $false
                $callback = [Win32+EnumWindowsProc] {{
                    param($hWnd, $lParam)
                    if ([Win32]::IsWindowVisible($hWnd)) {{
                        $len = [Win32]::GetWindowTextLength($hWnd)
                        if ($len -gt 0) {{
                            $sb = New-Object System.Text.StringBuilder($len + 1)
                            [Win32]::GetWindowText($hWnd, $sb, $sb.Capacity) | Out-Null
                            if ($sb.ToString() -like "*{title}*") {{
                                [Win32]::ShowWindow($hWnd, 9) | Out-Null
                                [Win32]::SetForegroundWindow($hWnd) | Out-Null
                                $found = $true
                                return $false
                            }}
                        }}
                    }}
                    return $true
                }}
                [Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
                $found
                """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0, "stdout": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def minimize_window(self, title: str = "", handle: int = 0) -> Dict[str, Any]:
        """Minimize window."""
        try:
            ps_script = f"""
            Add-Type @'
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {{
                [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
                [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
                [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
                public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            }}
'@
            if ({handle}) {{
                [Win32]::ShowWindow([IntPtr]::new({handle}), 6) | Out-Null
            }} else {{
                $callback = [Win32+EnumWindowsProc] {{
                    param($hWnd, $lParam)
                    if ([Win32]::IsWindowVisible($hWnd)) {{
                        $len = [Win32]::GetWindowTextLength($hWnd)
                        if ($len -gt 0) {{
                            $sb = New-Object System.Text.StringBuilder($len + 1)
                            [Win32]::GetWindowText($hWnd, $sb, $sb.Capacity) | Out-Null
                            if ($sb.ToString() -like "*{title}*") {{
                                [Win32]::ShowWindow($hWnd, 6) | Out-Null
                                return $false
                            }}
                        }}
                    }}
                    return $true
                }}
                [Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
            }}
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def maximize_window(self, title: str = "", handle: int = 0) -> Dict[str, Any]:
        """Maximize window."""
        try:
            ps_script = f"""
            Add-Type @'
            using System;
            using System.Runtime.InteropServices;
            public class Win32 {{
                [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
                [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
                [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
                public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            }}
'@
            if ({handle}) {{
                [Win32]::ShowWindow([IntPtr]::new({handle}), 3) | Out-Null
            }} else {{
                $callback = [Win32+EnumWindowsProc] {{
                    param($hWnd, $lParam)
                    if ([Win32]::IsWindowVisible($hWnd)) {{
                        $len = [Win32]::GetWindowTextLength($hWnd)
                        if ($len -gt 0) {{
                            $sb = New-Object System.Text.StringBuilder($len + 1)
                            [Win32]::GetWindowText($hWnd, $sb, $sb.Capacity) | Out-Null
                            if ($sb.ToString() -like "*{title}*") {{
                                [Win32]::ShowWindow($hWnd, 3) | Out-Null
                                return $false
                            }}
                        }}
                    }}
                    return $true
                }}
                [Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
            }}
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Screenshot ---

    def take_screenshot(self, path: str = "", monitor: int = 0) -> Dict[str, Any]:
        """Take screenshot of monitor (0 = all)."""
        try:
            from PIL import ImageGrab
            import tempfile

            if not path:
                path = str(Path(tempfile.gettempdir()) / f"myjarvis_screenshot_{int(time.time())}.png")

            if monitor == 0:
                img = ImageGrab.grab(all_screens=True)
            else:
                # Multi-monitor support
                img = ImageGrab.grab(all_screens=True)

            img.save(path)
            return {"success": True, "path": path, "size": img.size}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Command Execution ---

    def run_command(self, command: str, shell: str = "powershell", timeout: int = 30) -> Dict[str, Any]:
        """Run a shell command."""
        try:
            if shell == "powershell":
                cmd = ["powershell", "-NoProfile", "-Command", command]
            elif shell == "cmd":
                cmd = ["cmd", "/c", command]
            elif shell == "bash":
                cmd = ["bash", "-c", command]
            else:
                cmd = command if isinstance(command, list) else [command]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Shortcuts ---

    def send_shortcut(self, keys: str) -> Dict[str, Any]:
        """Send keyboard shortcut (e.g., 'win+d', 'ctrl+shift+esc', 'alt+f4')."""
        try:
            import pyautogui
            pyautogui.hotkey(*keys.lower().split("+"))
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Volume/Brightness ---

    def set_volume(self, level: int = None, mute: bool = False, change: int = 0) -> Dict[str, Any]:
        """Set system volume (0-100), mute, or change by delta."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)

            if mute:
                volume.SetMute(1, None)
                return {"success": True, "muted": True}

            if level is not None:
                # Convert 0-100 to 0.0-1.0
                scalar = max(0, min(100, level)) / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return {"success": True, "level": level}

            if change != 0:
                current = volume.GetMasterVolumeLevelScalar()
                new_level = max(0.0, min(1.0, current + change / 100.0))
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return {"success": True, "level": round(new_level * 100)}

            current = round(volume.GetMasterVolumeLevelScalar() * 100)
            muted = volume.GetMute()
            return {"success": True, "level": current, "muted": bool(muted)}

        except Exception as e:
            # Fallback to nircmd if available
            try:
                if mute:
                    subprocess.run(["nircmd", "mutesysvolume", "1"], check=True)
                elif level is not None:
                    subprocess.run(["nircmd", "setsysvolume", str(level * 65535 // 100)], check=True)
                elif change != 0:
                    subprocess.run(["nircmd", "changesysvolume", str(change * 65535 // 100)], check=True)
                return {"success": True, "fallback": "nircmd"}
            except Exception:
                return {"success": False, "error": str(e)}

    def set_brightness(self, level: int = None, change: int = 0) -> Dict[str, Any]:
        """Set screen brightness (0-100) or change by delta."""
        try:
            import wmi
            c = wmi.WMI(namespace='wmi')
            monitors = c.WmiMonitorBrightnessMethods()
            if not monitors:
                return {"success": False, "error": "No WMI brightness control available"}

            if level is not None:
                level = max(0, min(100, level))
                for m in monitors:
                    m.WmiSetBrightness(level, 0)
                return {"success": True, "level": level}

            if change != 0:
                # Get current and adjust
                brightness = c.WmiMonitorBrightness()
                if brightness:
                    current = brightness[0].CurrentBrightness
                    new_level = max(0, min(100, current + change))
                    for m in monitors:
                        m.WmiSetBrightness(new_level, 0)
                    return {"success": True, "level": new_level}

            brightness = c.WmiMonitorBrightness()
            current = brightness[0].CurrentBrightness if brightness else 0
            return {"success": True, "level": current}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Power ---

    def power_action(self, action: str) -> Dict[str, Any]:
        """Power action: sleep, hibernate, shutdown, restart, lock."""
        actions = {
            "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "hibernate": ["shutdown", "/h"],
            "shutdown": ["shutdown", "/s", "/t", "0"],
            "restart": ["shutdown", "/r", "/t", "0"],
            "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
        }

        if action not in actions:
            return {"success": False, "error": f"Unknown action: {action}. Valid: {list(actions.keys())}"}

        try:
            subprocess.run(actions[action], check=True)
            return {"success": True, "action": action}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Startup ---

    def manage_startup(self, action: str, app: str = "", path: str = "") -> Dict[str, Any]:
        """Manage startup apps: list, add, remove, enable, disable."""
        try:
            import winreg

            startup_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_ALL_ACCESS
            )

            if action == "list":
                apps = {}
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(startup_key, i)
                        apps[name] = value
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(startup_key)
                return {"success": True, "apps": apps}

            elif action == "add":
                if not app or not path:
                    return {"success": False, "error": "app and path required for add"}
                winreg.SetValueEx(startup_key, app, 0, winreg.REG_SZ, path)
                winreg.CloseKey(startup_key)
                return {"success": True, "added": app}

            elif action == "remove":
                if not app:
                    return {"success": False, "error": "app required for remove"}
                try:
                    winreg.DeleteValue(startup_key, app)
                    winreg.CloseKey(startup_key)
                    return {"success": True, "removed": app}
                except FileNotFoundError:
                    winreg.CloseKey(startup_key)
                    return {"success": False, "error": f"App {app} not in startup"}

            elif action in ("enable", "disable"):
                # Move to/from disabled key
                return {"success": False, "error": "enable/disable not implemented yet"}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}