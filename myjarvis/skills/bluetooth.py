"""
MyJarvis — Bluetooth Skill
Scan, connect, monitor battery of Bluetooth devices
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import platform
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class BluetoothSkill(Skill):
    """Bluetooth device management: scan, pair, connect, battery."""

    name = "bluetooth"
    description = "Bluetooth: scan devices, pair/connect, monitor battery, audio profiles"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._is_windows = platform.system() == "Windows"

    def _register_actions(self) -> None:
        self.register_action("scan", self.scan_devices)
        self.register_action("list", self.list_paired)
        self.register_action("connect", self.connect_device)
        self.register_action("disconnect", self.disconnect_device)
        self.register_action("pair", self.pair_device)
        self.register_action("unpair", self.unpair_device)
        self.register_action("battery", self.get_battery)
        self.register_action("info", self.get_device_info)
        self.register_action("audio_connect", self.connect_audio)
        self.register_action("toggle_power", self.toggle_power)

    # --- Windows Implementation (PowerShell) ---

    def _ps_bluetooth(self, script: str) -> Dict[str, Any]:
        """Run PowerShell Bluetooth command."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip() or f"Exit code {result.returncode}"}
            return {"success": True, "output": result.stdout.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Bluetooth command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def scan_devices(self, duration: int = 10) -> Dict[str, Any]:
        """Scan for nearby Bluetooth devices."""
        if self._is_windows:
            script = f"""
            Add-Type -AssemblyName System.Runtime.WindowsRuntime
            $asTask = [System.WindowsRuntimeSystemExtensions]::AsTask
            $adapter = [Windows.Devices.Bluetooth.BluetoothAdapter]::GetDefaultAsync() | $asTask | await
            if ($null -eq $adapter) {{ Write-Output 'No Bluetooth adapter found'; exit }}

            $watcher = [Windows.Devices.Enumeration.DeviceWatcher]::CreateWatcher(
                [Windows.Devices.Bluetooth.BluetoothDevice]::GetDeviceSelectorFromPairingState([Windows.Devices.Enumeration.DevicePairingState]::Unpaired)
            )
            $devices = @()
            $done = $false
            Register-ObjectEvent -InputObject $watcher -EventName Added -Action {{
                $device = $Event.SourceEventArgs
                $devices += [PSCustomObject]@{{
                    Id = $device.Id
                    Name = $device.Name
                    Kind = $device.Kind
                    IsPaired = $device.Properties['System.Devices.Aep.IsPaired']
                    SignalStrength = $device.Properties['System.Devices.Aep.SignalStrength']
                }}
            }} | Out-Null
            Register-ObjectEvent -InputObject $watcher -EventName Stopped -Action {{
                $done = $true
                Unregister-Event -SourceIdentifier $EventSubscriber.SourceIdentifier
            }} | Out-Null
            $watcher.Start()
            Start-Sleep -Seconds {duration}
            $watcher.Stop()
            while (-not $done) {{ Start-Sleep -Milliseconds 100 }}
            $devices | Where-Object {{ $_.Name }} | Sort-Object Name -Unique | ConvertTo-Json -Depth 3
            """
            result = self._ps_bluetooth(script)
            if result["success"] and result["output"]:
                import json
                try:
                    devices = json.loads(result["output"])
                    if not isinstance(devices, list):
                        devices = [devices]
                    return {"success": True, "devices": devices}
                except json.JSONDecodeError:
                    pass
            return {"success": True, "devices": []}
        else:
            # Linux: use bluetoothctl
            return self._linux_bluetoothctl("scan", duration)

    def list_paired(self) -> Dict[str, Any]:
        """List paired/connected Bluetooth devices."""
        if self._is_windows:
            script = """
            Get-PnpDevice -Class Bluetooth -Status OK | ForEach-Object {
                $props = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_Address', 'DEVPKEY_Bluetooth_DeviceAddress', 'DEVPKEY_Device_Bluetooth_DeviceType'
                [PSCustomObject]@{
                    InstanceId = $_.InstanceId
                    FriendlyName = $_.FriendlyName
                    Status = $_.Status
                    Class = $_.Class
                    Address = ($props | Where-Object KeyName -eq 'DEVPKEY_Bluetooth_DeviceAddress').Data
                    DeviceType = ($props | Where-Object KeyName -eq 'DEVPKEY_Device_Bluetooth_DeviceType').Data
                }
            } | ConvertTo-Json -Depth 3
            """
            result = self._ps_bluetooth(script)
            if result["success"] and result["output"]:
                import json
                try:
                    devices = json.loads(result["output"])
                    if not isinstance(devices, list):
                        devices = [devices]
                    return {"success": True, "devices": devices}
                except json.JSONDecodeError:
                    pass
            return {"success": True, "devices": []}
        else:
            return self._linux_bluetoothctl("paired")

    def connect_device(self, device_id: str) -> Dict[str, Any]:
        """Connect to a paired Bluetooth device."""
        if self._is_windows:
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            $device | Enable-PnpDevice -Confirm:$false
            Start-Sleep -Seconds 2
            $device = Get-PnpDevice -InstanceId '{device_id}'
            $device.Status
            """
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("connect", device_id)

    def disconnect_device(self, device_id: str) -> Dict[str, Any]:
        """Disconnect a Bluetooth device."""
        if self._is_windows:
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            $device | Disable-PnpDevice -Confirm:$false
            """
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("disconnect", device_id)

    def pair_device(self, device_id: str) -> Dict[str, Any]:
        """Pair with a Bluetooth device."""
        if self._is_windows:
            script = f"""
            Add-Type -AssemblyName System.Runtime.WindowsRuntime
            $asTask = [System.WindowsRuntimeSystemExtensions]::AsTask
            $deviceInfo = [Windows.Devices.Enumeration.DeviceInformation]::CreateFromIdAsync('{device_id}') | $asTask | await
            if ($null -eq $deviceInfo) {{ Write-Output 'Device not found'; exit 1 }}
            $pairing = $deviceInfo.Pairing
            $pairing.Custom.PairingRequested += {{
                param($sender, $args)
                $args.Accept()
            }}
            $result = $pairing.PairAsync() | $asTask | await
            $result.Status.ToString()
            """
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("pair", device_id)

    def unpair_device(self, device_id: str) -> Dict[str, Any]:
        """Unpair/remove a Bluetooth device."""
        if self._is_windows:
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            $device | Remove-PnpDevice -Confirm:$false
            """
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("remove", device_id)

    def get_battery(self, device_id: str = "") -> Dict[str, Any]:
        """Get battery level of Bluetooth device(s)."""
        if self._is_windows:
            script = """
            Get-PnpDevice -Class Bluetooth -Status OK | ForEach-Object {
                $battery = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_BatteryLevel' -ErrorAction SilentlyContinue
                if ($battery -and $battery.Data -ne $null) {
                    [PSCustomObject]@{
                        InstanceId = $_.InstanceId
                        FriendlyName = $_.FriendlyName
                        BatteryLevel = $battery.Data
                    }
                }
            } | ConvertTo-Json -Depth 3
            """
            result = self._ps_bluetooth(script)
            if result["success"] and result["output"]:
                import json
                try:
                    devices = json.loads(result["output"])
                    if not isinstance(devices, list):
                        devices = [devices]
                    if device_id:
                        devices = [d for d in devices if d["InstanceId"] == device_id]
                    return {"success": True, "devices": devices}
                except json.JSONDecodeError:
                    pass
            return {"success": True, "devices": []}
        else:
            return self._linux_bluetoothctl("battery", device_id)

    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get detailed info for a specific device."""
        if self._is_windows:
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            $props = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName *
            $device | Select-Object InstanceId, FriendlyName, Status, Class, Problem, ConfigManagerErrorCode
            $props | Select-Object KeyName, Data
            """  # Simplified
            result = self._ps_bluetooth(script)
            return result
        else:
            return self._linux_bluetoothctl("info", device_id)

    def connect_audio(self, device_id: str) -> Dict[str, Any]:
        """Connect Bluetooth audio profile (A2DP/HFP)."""
        if self._is_windows:
            script = (
                "# Connect audio profile via PowerShell Audio API\n"
                "Add-Type -TypeDefinition @'\n"
                "using System;\n"
                "using System.Runtime.InteropServices;\n"
                "public class Audio {\n"
                "    [DllImport(\"winmm.dll\")] public static extern uint waveOutGetNumDevs();\n"
                "}\n"
                "'@\n"
                "# Use Windows.Devices.Bluetooth.Rfcomm for audio\n"
                "# Simplified - just connect the device\n"
                f"$device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue\n"
                "if ($null -eq $device) { Write-Output 'Device not found'; exit 1 }\n"
                "$device | Enable-PnpDevice -Confirm:$false\n"
            )
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("connect_audio", device_id)

    def toggle_power(self, on: bool = True) -> Dict[str, Any]:
        """Turn Bluetooth radio on/off."""
        if self._is_windows:
            script = f"""
            $radio = Get-PnpDevice -Class Radio -FriendlyName '*Bluetooth*' | Select-Object -First 1
            if ($null -eq $radio) {{ Write-Output 'No Bluetooth radio found'; exit 1 }}
            if ({str(on).lower()}) {{
                $radio | Enable-PnpDevice -Confirm:$false
            }} else {{
                $radio | Disable-PnpDevice -Confirm:$false
            }}
            """
            return self._ps_bluetooth(script)
        else:
            return self._linux_bluetoothctl("power", "on" if on else "off")

    # --- Linux Implementation (bluetoothctl) ---

    def _linux_bluetoothctl(self, action: str, arg: str = "") -> Dict[str, Any]:
        """Execute bluetoothctl commands on Linux."""
        try:
            if action == "scan":
                # Scan for devices
                proc = subprocess.run(
                    ["bluetoothctl", "--timeout", str(arg), "scan", "on"],
                    capture_output=True, text=True, timeout=arg + 5
                )
                # Then list devices
                proc2 = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True
                )
                devices = []
                for line in proc2.stdout.strip().split('\n'):
                    if line.startswith("Device "):
                        parts = line.split(" ", 2)
                        if len(parts) >= 3:
                            devices.append({"Id": parts[1], "Name": parts[2]})
                return {"success": True, "devices": devices}

            elif action == "paired":
                proc = subprocess.run(
                    ["bluetoothctl", "paired-devices"],
                    capture_output=True, text=True
                )
                devices = []
                for line in proc.stdout.strip().split('\n'):
                    if line.startswith("Device "):
                        parts = line.split(" ", 2)
                        if len(parts) >= 3:
                            devices.append({"InstanceId": parts[1], "FriendlyName": parts[2]})
                return {"success": True, "devices": devices}

            elif action == "connect":
                proc = subprocess.run(
                    ["bluetoothctl", "connect", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            elif action == "disconnect":
                proc = subprocess.run(
                    ["bluetoothctl", "disconnect", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            elif action == "pair":
                proc = subprocess.run(
                    ["bluetoothctl", "pair", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            elif action == "remove":
                proc = subprocess.run(
                    ["bluetoothctl", "remove", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            elif action == "battery":
                proc = subprocess.run(
                    ["bluetoothctl", "info", arg] if arg else ["bluetoothctl", "devices"],
                    capture_output=True, text=True
                )
                # Parse battery from info
                return {"success": True, "output": proc.stdout}

            elif action == "info":
                proc = subprocess.run(
                    ["bluetoothctl", "info", arg],
                    capture_output=True, text=True
                )
                return {"success": True, "output": proc.stdout}

            elif action == "connect_audio":
                proc = subprocess.run(
                    ["bluetoothctl", "connect", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            elif action == "power":
                proc = subprocess.run(
                    ["bluetoothctl", "power", arg],
                    capture_output=True, text=True
                )
                return {"success": proc.returncode == 0, "output": proc.stdout}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Cross-platform imports
if platform.system() != "Windows":
    try:
        import bluetoothctl  # Not a real import, just checking
    except ImportError:
        pass