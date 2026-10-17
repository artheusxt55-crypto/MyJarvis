"""
MyJarvis — Screenshot Skill
Capture screen, window, region with OCR
"""
from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class ScreenshotSkill(Skill):
    """Screenshot: full screen, window, region, OCR."""

    name = "screenshot"
    description = "Screenshot: capture screen/window/region, OCR text extraction"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._is_windows = True  # Windows-only for now

    def _register_actions(self) -> None:
        self.register_action("capture", self.capture_screen)
        self.register_action("window", self.capture_window)
        self.register_action("region", self.capture_region)
        self.register_action("ocr", self.ocr_image)
        self.register_action("ocr_screen", self.ocr_screen)

    def capture_screen(self, path: str = "", monitor: int = 0) -> Dict[str, Any]:
        """Capture full screen (or specific monitor)."""
        try:
            from PIL import ImageGrab

            if not path:
                path = str(Path(tempfile.gettempdir()) / f"myjarvis_screen_{int(time.time())}.png")

            if monitor == 0:
                img = ImageGrab.grab(all_screens=True)
            else:
                # Multi-monitor: grab all then crop (simplified)
                img = ImageGrab.grab(all_screens=True)

            img.save(path)
            return {"success": True, "path": path, "size": img.size, "mode": img.mode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def capture_window(self, title: str = "", handle: int = 0, path: str = "") -> Dict[str, Any]:
        """Capture specific window by title or handle."""
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image

            if not path:
                path = str(Path(tempfile.gettempdir()) / f"myjarvis_window_{int(time.time())}.png")

            if handle:
                hwnd = handle
            else:
                # Find window by title
                hwnd = None
                def enum_windows(hwnd, results):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        if title.lower() in window_title.lower():
                            results.append(hwnd)
                    return True

                results = []
                win32gui.EnumWindows(enum_windows, results)
                if not results:
                    return {"success": False, "error": f"Window '{title}' not found"}
                hwnd = results[0]

            # Get window rect
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            # Capture
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

            # Save to PIL Image
            bmp_info = bitmap.GetInfo()
            bmp_str = bitmap.GetBitmapBits(True)
            img = Image.frombuffer(
                "RGB",
                (bmp_info["bmWidth"], bmp_info["bmHeight"]),
                bmp_str, "raw", "BGRX", 0, 1
            )

            # Cleanup
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)

            img.save(path)
            return {"success": True, "path": path, "size": img.size, "window_title": win32gui.GetWindowText(hwnd)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def capture_region(self, left: int, top: int, width: int, height: int, path: str = "") -> Dict[str, Any]:
        """Capture specific screen region."""
        try:
            from PIL import ImageGrab

            if not path:
                path = str(Path(tempfile.gettempdir()) / f"myjarvis_region_{int(time.time())}.png")

            bbox = (left, top, left + width, top + height)
            img = ImageGrab.grab(bbox=bbox)
            img.save(path)
            return {"success": True, "path": path, "size": img.size, "bbox": bbox}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ocr_image(self, path: str, lang: str = "por") -> Dict[str, Any]:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(path)
            text = pytesseract.image_to_string(img, lang=lang)
            return {"success": True, "text": text.strip(), "path": path}
        except ImportError:
            return {"success": False, "error": "pytesseract not installed: pip install pytesseract && tesseract-ocr"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ocr_screen(self, lang: str = "por", region: List[int] = None) -> Dict[str, Any]:
        """Capture screen and OCR in one step."""
        try:
            from PIL import ImageGrab
            import pytesseract

            if region:
                bbox = tuple(region)
                img = ImageGrab.grab(bbox=bbox)
            else:
                img = ImageGrab.grab(all_screens=True)

            text = pytesseract.image_to_string(img, lang=lang)
            return {"success": True, "text": text.strip()}
        except ImportError:
            return {"success": False, "error": "pytesseract not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}