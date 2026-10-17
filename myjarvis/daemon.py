"""
MyJarvis — Daemon (Windows Service + Background)
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis
from myjarvis.ipc.bridge import IPCBridge

logger = logging.getLogger(__name__)


class MyJarvisDaemon:
    """MyJarvis daemon: runs Jarvis + IPC bridge in background."""

    def __init__(self, config_path: Optional[Path] = None, foreground: bool = False):
        self.config_path = config_path
        self.foreground = foreground
        self._jarvis: Optional[MyJarvis] = None
        self._ipc_bridge: Optional[IPCBridge] = None
        self._running = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def run(self) -> None:
        """Run daemon (blocking)."""
        if self.foreground:
            self._run_foreground()
        else:
            self._run_background()

    def _run_foreground(self) -> None:
        """Run in foreground (for debugging)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._main_loop = loop

        try:
            loop.run_until_complete(self._start())
            loop.run_until_complete(self._run_loop())
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            loop.run_until_complete(self._stop())
            loop.close()

    def _run_background(self) -> None:
        """Run in background thread."""
        self._thread = threading.Thread(target=self._run_foreground, daemon=True)
        self._thread.start()
        logger.info("Daemon started in background")

    async def _start(self) -> None:
        """Initialize Jarvis and IPC."""
        logger.info("Starting MyJarvis daemon...")

        # Load config
        config = load_config(self.config_path)

        # Initialize Jarvis
        self._jarvis = MyJarvis(config=config)

        # Start IPC bridge
        ipc_config = getattr(config, "myjarvis_ipc", {})
        if ipc_config.get("enabled", True):
            self._ipc_bridge = IPCBridge(
                host=ipc_config.get("host", "127.0.0.1"),
                port=ipc_config.get("port", 8765),
                jarvis=self._jarvis,
            )
            await self._ipc_bridge.start()
            logger.info("IPC bridge started")

        # Start scheduler if enabled
        if self._jarvis.skills:
            schedule_skill = self._jarvis.skills.get("schedule")
            if schedule_skill:
                schedule_skill.start_scheduler()

        self._running = True
        logger.info("MyJarvis daemon started")

    async def _run_loop(self) -> None:
        """Main event loop."""
        while self._running:
            await asyncio.sleep(1)

    async def _stop(self) -> None:
        """Stop daemon gracefully."""
        logger.info("Stopping MyJarvis daemon...")
        self._running = False

        if self._ipc_bridge:
            await self._ipc_bridge.stop()

        if self._jarvis:
            self._jarvis.close()

        logger.info("MyJarvis daemon stopped")

    def stop(self) -> None:
        """Stop daemon (thread-safe)."""
        if self._main_loop and self._running:
            asyncio.run_coroutine_threadsafe(self._stop(), self._main_loop)

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status."""
        status = {
            "running": self._running,
            "foreground": self.foreground,
        }
        if self._jarvis:
            status.update({
                "engine": self._jarvis._resolved_engine_key,
                "model": self._jarvis._config.intelligence.default_model,
                "skills_loaded": list(self._jarvis.skills.skills.keys()) if self._jarvis.skills else [],
                "ipc_connected": len(self._ipc_bridge._clients) if self._ipc_bridge else 0,
            })
        return status


# Singleton instance
_daemon_instance: Optional[MyJarvisDaemon] = None


def get_daemon(config_path: Optional[Path] = None, foreground: bool = False) -> MyJarvisDaemon:
    """Get or create daemon singleton."""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = MyJarvisDaemon(config_path=config_path, foreground=foreground)
    return _daemon_instance


def run_daemon(foreground: bool = False, config_path: Optional[Path] = None) -> None:
    """Entry point for daemon."""
    daemon = get_daemon(config_path=config_path, foreground=foreground)
    daemon.run()


def get_daemon_status() -> Dict[str, Any]:
    """Get daemon status."""
    if _daemon_instance:
        return _daemon_instance.get_status()
    return {"running": False}