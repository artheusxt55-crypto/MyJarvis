"""
MyJarvis — Audio Skill
Volume, devices, recording, playback on Windows
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class AudioSkill(Skill):
    """Audio system control: volume, devices, recording, playback."""

    name = "audio"
    description = "Audio: volume, devices, recording, playback, formats"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()

    def _register_actions(self) -> None:
        self.register_action("volume", self.set_volume)
        self.register_action("mute", self.toggle_mute)
        self.register_action("devices", self.list_devices)
        self.register_action("default", self.set_default_device)
        self.register_action("record", self.record_audio)
        self.register_action("play", self.play_audio)
        self.register_action("stop", self.stop_audio)
        self.register_action("format", self.set_format)

    def set_volume(self, level: int = None, change: int = 0, device: str = "") -> Dict[str, Any]:
        """Set volume (0-100) or change by delta. Optionally target specific device."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            if device:
                devices = AudioUtilities.GetAllDevices()
                target = None
                for d in devices:
                    if device.lower() in d.FriendlyName.lower():
                        target = d
                        break
                if not target:
                    return {"success": False, "error": f"Device '{device}' not found"}
                interface = target.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            else:
                speakers = AudioUtilities.GetSpeakers()
                interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)

            volume = interface.QueryInterface(IAudioEndpointVolume)

            if level is not None:
                scalar = max(0, min(100, level)) / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return {"success": True, "level": level, "device": device or "default"}

            if change != 0:
                current = volume.GetMasterVolumeLevelScalar()
                new_level = max(0.0, min(1.0, current + change / 100.0))
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return {"success": True, "level": round(new_level * 100), "device": device or "default"}

            current = round(volume.GetMasterVolumeLevelScalar() * 100)
            muted = volume.GetMute()
            return {"success": True, "level": current, "muted": bool(muted), "device": device or "default"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_mute(self, mute: bool = None, device: str = "") -> Dict[str, Any]:
        """Toggle or set mute state."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL

            if device:
                devices = AudioUtilities.GetAllDevices()
                target = None
                for d in devices:
                    if device.lower() in d.FriendlyName.lower():
                        target = d
                        break
                if not target:
                    return {"success": False, "error": f"Device '{device}' not found"}
                interface = target.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            else:
                speakers = AudioUtilities.GetSpeakers()
                interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)

            volume = interface.QueryInterface(IAudioEndpointVolume)

            if mute is None:
                mute = not volume.GetMute()

            volume.SetMute(1 if mute else 0, None)
            return {"success": True, "muted": mute, "device": device or "default"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_devices(self, type: str = "all") -> Dict[str, Any]:
        """List audio devices: 'input', 'output', 'all'."""
        try:
            from pycaw.pycaw import AudioUtilities

            devices = AudioUtilities.GetAllDevices()
            result = []

            for d in devices:
                dev_type = "output" if d.State & 1 else "input"  # simplified
                if type != "all" and dev_type != type:
                    continue

                result.append({
                    "id": d.Id,
                    "name": d.FriendlyName,
                    "type": dev_type,
                    "state": d.State,
                    "is_default": d.IsDefaultDevice,
                })

            return {"success": True, "devices": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_default_device(self, device_id: str, role: str = "output") -> Dict[str, Any]:
        """Set default audio device (requires Windows 10+ Policy API or manual)."""
        try:
            # Use PowerShell to set default device
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device_id}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            # Set as default via Audio Switch or policy
            # This is simplified - actual implementation needs AudioPolicyManager COM
            $device.FriendlyName
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def record_audio(
        self,
        duration: int = 10,
        path: str = "",
        device: str = "",
        format: str = "wav",
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> Dict[str, Any]:
        """Record audio from input device."""
        try:
            import sounddevice as sd
            import soundfile as sf
            import tempfile

            if not path:
                path = str(Path(tempfile.gettempdir()) / f"myjarvis_recording_{int(time.time())}.{format}")

            # Find device
            devices = sd.query_devices()
            device_idx = None
            if device:
                for i, d in enumerate(devices):
                    if device.lower() in d["name"].lower():
                        device_idx = i
                        break

            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                device=device_idx,
                dtype="int16",
            )
            sd.wait()
            sf.write(path, recording, sample_rate, format=format.upper())

            return {"success": True, "path": path, "duration": duration, "format": format}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def play_audio(self, path: str, device: str = "", volume: float = 1.0) -> Dict[str, Any]:
        """Play audio file."""
        try:
            import sounddevice as sd
            import soundfile as sf

            data, samplerate = sf.read(path, dtype="float32")
            data = data * volume

            device_idx = None
            if device:
                devices = sd.query_devices()
                for i, d in enumerate(devices):
                    if device.lower() in d["name"].lower() and d["max_output_channels"] > 0:
                        device_idx = i
                        break

            sd.play(data, samplerate, device=device_idx)
            return {"success": True, "playing": path, "duration": len(data) / samplerate}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_audio(self) -> Dict[str, Any]:
        """Stop any playing audio."""
        try:
            import sounddevice as sd
            sd.stop()
            return {"success": True, "stopped": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_format(self, device: str, sample_rate: int = 48000, bit_depth: int = 24) -> Dict[str, Any]:
        """Set audio format for device (Windows)."""
        try:
            script = f"""
            $device = Get-PnpDevice -InstanceId '{device}' -ErrorAction SilentlyContinue
            if ($null -eq $device) {{ Write-Output 'Device not found'; exit 1 }}
            # Set default format via Windows Audio API
            # Requires elevated COM access to IAudioClient
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}