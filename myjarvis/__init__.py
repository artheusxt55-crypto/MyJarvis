"""
MyJarvis — Personal AI Assistant Daemon
ALFRED personality, Windows-native, always-on
"""
from __future__ import annotations

__version__ = "1.0.0"
__author__ = "herog"
__description__ = "Personal AI assistant daemon with ALFRED personality"

from myjarvis.core.config import load_config, get_config_path, get_myjarvis_dir
from myjarvis.core.jarvis import MyJarvis
from myjarvis.daemon import run_daemon, get_daemon_status
from myjarvis.tray import run_tray

__all__ = [
    "load_config",
    "get_config_path",
    "get_myjarvis_dir",
    "MyJarvis",
    "run_daemon",
    "get_daemon_status",
    "run_tray",
    "__version__",
]