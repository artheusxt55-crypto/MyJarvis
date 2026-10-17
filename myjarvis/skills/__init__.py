"""
MyJarvis — Skills Package
"""
from __future__ import annotations

# Import all skills for registry auto-discovery
from myjarvis.skills.windows_control import WindowsControlSkill
from myjarvis.skills.bluetooth import BluetoothSkill
from myjarvis.skills.audio import AudioSkill
from myjarvis.skills.filesystem import FileSystemSkill
from myjarvis.skills.process import ProcessSkill
from myjarvis.skills.network import NetworkSkill
from myjarvis.skills.power import PowerSkill
from myjarvis.skills.schedule import ScheduleSkill
from myjarvis.skills.clipboard import ClipboardSkill
from myjarvis.skills.screenshot import ScreenshotSkill

__all__ = [
    "WindowsControlSkill",
    "BluetoothSkill",
    "AudioSkill",
    "FileSystemSkill",
    "ProcessSkill",
    "NetworkSkill",
    "PowerSkill",
    "ScheduleSkill",
    "ClipboardSkill",
    "ScreenshotSkill",
]