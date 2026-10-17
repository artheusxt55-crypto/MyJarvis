"""
MyJarvis — System Tray Icon (Windows)
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from myjarvis.daemon import get_daemon, run_daemon, get_daemon_status

logger = logging.getLogger(__name__)


class TrayIcon:
    """System tray icon for MyJarvis daemon."""

    def __init__(self):
        self._icon: Optional[pystray.Icon] = None
        self._daemon = None
        self._running = False

    def _create_icon_image(self) -> Image.Image:
        """Create tray icon image."""
        # Create a simple J icon
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle
        draw.ellipse([4, 4, 60, 60], fill="#1a1a2e", outline="#00d4ff", width=3)

        # J letter
        draw.text((18, 12), "J", fill="#00d4ff", font_size=36)

        # Status indicator (green dot)
        draw.ellipse([48, 48, 60, 60], fill="#00ff88", outline="#1a1a2e", width=2)

        return img

    def _get_menu(self) -> pystray.Menu:
        """Create tray menu."""
        return pystray.Menu(
            pystray.MenuItem("MyJarvis", self._on_show_status, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Status", self._on_show_status),
            pystray.MenuItem("Open Logs", self._on_open_logs),
            pystray.MenuItem("Open Config", self._on_open_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart Daemon", self._on_restart),
            pystray.MenuItem("Stop Daemon", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit),
        )

    def run(self, daemon_foreground: bool = False) -> None:
        """Run tray icon (blocking)."""
        # Start daemon in background if not foreground
        if not daemon_foreground:
            daemon_thread = threading.Thread(target=run_daemon, kwargs={"foreground": False}, daemon=True)
            daemon_thread.start()
            self._daemon = get_daemon()

        # Create and run icon
        self._icon = pystray.Icon(
            "myjarvis",
            self._create_icon_image(),
            "MyJarvis",
            self._get_menu(),
        )
        self._running = True

        # Update icon periodically
        def update_icon():
            import time
            while self._running:
                time.sleep(5)
                if self._icon:
                    # Update status indicator color
                    status = get_daemon_status()
                    if status.get("running"):
                        # Could update icon here
                        pass

        update_thread = threading.Thread(target=update_icon, daemon=True)
        update_thread.start()

        logger.info("Tray icon running")
        self._icon.run()

    def stop(self) -> None:
        """Stop tray icon."""
        self._running = False
        if self._icon:
            self._icon.stop()

    # --- Menu Callbacks ---

    def _on_show_status(self, icon, item) -> None:
        """Show status notification."""
        status = get_daemon_status()
        msg = f"MyJarvis: {'Running' if status.get('running') else 'Stopped'}"
        if status.get("running"):
            msg += f"\nEngine: {status.get('engine', 'N/A')}"
            msg += f"\nModel: {status.get('model', 'N/A')}"
            msg += f"\nIPC Clients: {status.get('ipc_connected', 0)}"
        icon.notify(msg, "MyJarvis Status")

    def _on_open_logs(self, icon, item) -> None:
        """Open logs folder."""
        log_dir = Path("~/.myjarvis/logs").expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(log_dir))

    def _on_open_config(self, icon, item) -> None:
        """Open config file."""
        config_path = Path("~/.myjarvis/config.toml").expanduser()
        if config_path.exists():
            os.startfile(str(config_path))
        else:
            icon.notify("Config file not found", "MyJarvis")

    def _on_restart(self, icon, item) -> None:
        """Restart daemon."""
        if self._daemon:
            self._daemon.stop()
        # Restart in background
        daemon_thread = threading.Thread(target=run_daemon, kwargs={"foreground": False}, daemon=True)
        daemon_thread.start()
        self._daemon = get_daemon()
        icon.notify("Daemon restarting...", "MyJarvis")

    def _on_stop(self, icon, item) -> None:
        """Stop daemon."""
        if self._daemon:
            self._daemon.stop()
        icon.notify("Daemon stopped", "MyJarvis")

    def _on_exit(self, icon, item) -> None:
        """Exit application."""
        self.stop()
        if self._daemon:
            self._daemon.stop()
        sys.exit(0)


def run_tray(daemon_foreground: bool = False) -> None:
    """Entry point for tray icon."""
    tray = TrayIcon()
    try:
        tray.run(daemon_foreground=daemon_foreground)
    except KeyboardInterrupt:
        tray.stop()