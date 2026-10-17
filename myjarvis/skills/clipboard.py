"""
MyJarvis — Clipboard Skill
Clipboard history, manipulation, monitoring
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class ClipboardSkill(Skill):
    """Clipboard management: history, get, set, monitor, clear."""

    name = "clipboard"
    description = "Clipboard: history, get/set, monitor changes, clear"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._history: List[Dict] = []
        self._max_history = 100
        self._monitoring = False
        self._last_content = ""
        self._storage_path = Path("~/.myjarvis/clipboard_history.json").expanduser()
        self._load_history()

    def _register_actions(self) -> None:
        self.register_action("get", self.get_clipboard)
        self.register_action("set", self.set_clipboard)
        self.register_action("history", self.get_history)
        self.register_action("clear", self.clear_history)
        self.register_action("monitor", self.start_monitor)
        self.register_action("unmonitor", self.stop_monitor)
        self.register_action("paste", self.paste)

    def _load_history(self) -> None:
        """Load clipboard history from storage."""
        if self._storage_path.exists():
            try:
                import json
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load clipboard history: {e}")

    def _save_history(self) -> None:
        """Save clipboard history to storage."""
        try:
            import json
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._history[-self._max_history:], f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save clipboard history: {e}")

    def _add_to_history(self, content: str, source: str = "unknown") -> None:
        """Add item to history."""
        if not content or content == self._last_content:
            return

        item = {
            "content": content,
            "timestamp": time.time(),
            "source": source,
            "length": len(content),
        }
        self._history.append(item)
        self._last_content = content

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        self._save_history()

    # --- Actions ---

    def get_clipboard(self) -> Dict[str, Any]:
        """Get current clipboard content."""
        try:
            import pyperclip
            content = pyperclip.paste()
            return {"success": True, "content": content, "length": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_clipboard(self, content: str) -> Dict[str, Any]:
        """Set clipboard content."""
        try:
            import pyperclip
            pyperclip.copy(content)
            self._add_to_history(content, "set")
            return {"success": True, "length": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get clipboard history."""
        return {
            "success": True,
            "history": self._history[-limit:],
            "count": len(self._history),
        }

    def clear_history(self) -> Dict[str, Any]:
        """Clear clipboard history."""
        self._history = []
        self._save_history()
        return {"success": True, "cleared": True}

    def start_monitor(self, interval: float = 0.5) -> Dict[str, Any]:
        """Start monitoring clipboard for changes."""
        if self._monitoring:
            return {"success": False, "error": "Already monitoring"}

        self._monitoring = True

        def monitor_loop():
            import pyperclip
            while self._monitoring:
                try:
                    content = pyperclip.paste()
                    if content and content != self._last_content:
                        self._add_to_history(content, "monitor")
                except Exception:
                    pass
                time.sleep(interval)

        import threading
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()

        return {"success": True, "monitoring": True, "interval": interval}

    def stop_monitor(self) -> Dict[str, Any]:
        """Stop monitoring clipboard."""
        if not self._monitoring:
            return {"success": False, "error": "Not monitoring"}

        self._monitoring = False
        return {"success": True, "monitoring": False}

    def paste(self) -> Dict[str, Any]:
        """Simulate paste (Ctrl+V)."""
        try:
            import pyautogui
            pyautogui.hotkey("ctrl", "v")
            return {"success": True, "pasted": True}
        except Exception as e:
            return {"success": False, "error": str(e)}