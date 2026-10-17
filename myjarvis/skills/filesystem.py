"""
MyJarvis — FileSystem Skill
File operations: search, read, write, watch
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class FileSystemSkill(Skill):
    """File system operations: search, read, write, copy, move, watch."""

    name = "filesystem"
    description = "Files: search, read, write, copy, move, delete, watch, metadata"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._watchers: Dict[str, Any] = {}

    def _register_actions(self) -> None:
        self.register_action("search", self.search_files)
        self.register_action("read", self.read_file)
        self.register_action("write", self.write_file)
        self.register_action("append", self.append_file)
        self.register_action("copy", self.copy_file)
        self.register_action("move", self.move_file)
        self.register_action("delete", self.delete_file)
        self.register_action("mkdir", self.make_dir)
        self.register_action("list", self.list_dir)
        self.register_action("info", self.file_info)
        self.register_action("hash", self.file_hash)
        self.register_action("watch", self.watch_path)
        self.register_action("unwatch", self.unwatch_path)

    def search_files(
        self,
        pattern: str,
        path: str = ".",
        recursive: bool = True,
        case_sensitive: bool = False,
        file_type: str = "",
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Search files by name/pattern."""
        try:
            root = Path(path).expanduser().resolve()
            if not root.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            matches = []
            if recursive:
                glob_pattern = f"**/{pattern}"
                for f in root.glob(glob_pattern):
                    if file_type and f.suffix.lower() != file_type.lower():
                        continue
                    if not case_sensitive and pattern.lower() not in f.name.lower():
                        continue
                    matches.append(self._file_info(f))
                    if len(matches) >= max_results:
                        break
            else:
                for f in root.glob(pattern):
                    if file_type and f.suffix.lower() != file_type.lower():
                        continue
                    matches.append(self._file_info(f))
                    if len(matches) >= max_results:
                        break

            return {"success": True, "matches": matches, "count": len(matches)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, path: str, encoding: str = "utf-8", max_size: int = 10_000_000) -> Dict[str, Any]:
        """Read file content."""
        try:
            fpath = Path(path).expanduser().resolve()
            if not fpath.exists():
                return {"success": False, "error": f"File not found: {path}"}
            if not fpath.is_file():
                return {"success": False, "error": f"Not a file: {path}"}
            if fpath.stat().st_size > max_size:
                return {"success": False, "error": f"File too large ({fpath.stat().st_size} > {max_size})"}

            content = fpath.read_text(encoding=encoding)
            return {"success": True, "content": content, "path": str(fpath), "size": fpath.stat().st_size}

        except UnicodeDecodeError:
            return {"success": False, "error": f"Cannot decode as {encoding}, try binary"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True) -> Dict[str, Any]:
        """Write file content."""
        try:
            fpath = Path(path).expanduser().resolve()
            if create_dirs:
                fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding=encoding)
            return {"success": True, "path": str(fpath), "size": len(content.encode(encoding))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append_file(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Append to file."""
        try:
            fpath = Path(path).expanduser().resolve()
            fpath.parent.mkdir(parents=True, exist_ok=True)
            with open(fpath, "a", encoding=encoding) as f:
                f.write(content)
            return {"success": True, "path": str(fpath), "appended": len(content.encode(encoding))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def copy_file(self, src: str, dst: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copy file or directory."""
        try:
            src_path = Path(src).expanduser().resolve()
            dst_path = Path(dst).expanduser().resolve()

            if not src_path.exists():
                return {"success": False, "error": f"Source not found: {src}"}

            if dst_path.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {dst}"}

            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src_path, dst_path)

            return {"success": True, "src": str(src_path), "dst": str(dst_path)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, src: str, dst: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move/rename file or directory."""
        try:
            src_path = Path(src).expanduser().resolve()
            dst_path = Path(dst).expanduser().resolve()

            if not src_path.exists():
                return {"success": False, "error": f"Source not found: {src}"}

            if dst_path.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {dst}"}

            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))

            return {"success": True, "src": str(src_path), "dst": str(dst_path)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """Delete file or directory."""
        try:
            fpath = Path(path).expanduser().resolve()
            if not fpath.exists():
                return {"success": False, "error": f"Not found: {path}"}

            if fpath.is_dir():
                if recursive:
                    shutil.rmtree(fpath)
                else:
                    fpath.rmdir()  # only empty
            else:
                fpath.unlink()

            return {"success": True, "deleted": str(fpath)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def make_dir(self, path: str, parents: bool = True, exist_ok: bool = True) -> Dict[str, Any]:
        """Create directory."""
        try:
            fpath = Path(path).expanduser().resolve()
            fpath.mkdir(parents=parents, exist_ok=exist_ok)
            return {"success": True, "path": str(fpath)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, path: str = ".", include_hidden: bool = False, sort: str = "name") -> Dict[str, Any]:
        """List directory contents."""
        try:
            root = Path(path).expanduser().resolve()
            if not root.exists() or not root.is_dir():
                return {"success": False, "error": f"Not a directory: {path}"}

            items = []
            for f in root.iterdir():
                if not include_hidden and f.name.startswith("."):
                    continue
                items.append(self._file_info(f))

            if sort == "name":
                items.sort(key=lambda x: x["name"].lower())
            elif sort == "size":
                items.sort(key=lambda x: x.get("size", 0), reverse=True)
            elif sort == "modified":
                items.sort(key=lambda x: x.get("modified", 0), reverse=True)

            return {"success": True, "items": items, "count": len(items), "path": str(root)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed file information."""
        try:
            fpath = Path(path).expanduser().resolve()
            if not fpath.exists():
                return {"success": False, "error": f"Not found: {path}"}
            return {"success": True, "info": self._file_info(fpath)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_hash(self, path: str, algorithm: str = "sha256") -> Dict[str, Any]:
        """Compute file hash."""
        try:
            import hashlib
            fpath = Path(path).expanduser().resolve()
            if not fpath.is_file():
                return {"success": False, "error": f"Not a file: {path}"}

            h = hashlib.new(algorithm)
            with open(fpath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)

            return {"success": True, "path": str(fpath), "algorithm": algorithm, "hash": h.hexdigest()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def watch_path(self, path: str, events: List[str] = None, recursive: bool = True) -> Dict[str, Any]:
        """Watch path for changes (requires watchdog)."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            fpath = Path(path).expanduser().resolve()
            if not fpath.exists():
                return {"success": False, "error": f"Path not found: {path}"}

            events = events or ["modified", "created", "deleted", "moved"]

            class WatchHandler(FileSystemEventHandler):
                def __init__(self, skill):
                    self.skill = skill

                def on_any_event(self, event):
                    if event.event_type in events:
                        self.skill._on_file_event(event)

            handler = WatchHandler(self)
            observer = Observer()
            observer.schedule(handler, str(fpath), recursive=recursive)
            observer.start()

            watcher_id = str(fpath)
            self._watchers[watcher_id] = {"observer": observer, "handler": handler, "path": fpath}

            return {"success": True, "watching": str(fpath), "watcher_id": watcher_id}

        except ImportError:
            return {"success": False, "error": "watchdog not installed: pip install watchdog"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unwatch_path(self, watcher_id: str = "", path: str = "") -> Dict[str, Any]:
        """Stop watching a path."""
        try:
            target_id = watcher_id or str(Path(path).expanduser().resolve())
            if target_id not in self._watchers:
                return {"success": False, "error": f"Watcher not found: {target_id}"}

            watcher = self._watchers[target_id]
            watcher["observer"].stop()
            watcher["observer"].join()
            del self._watchers[target_id]

            return {"success": True, "stopped": target_id}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _on_file_event(self, event) -> None:
        """Handle file system event (can be extended for notifications)."""
        logger.debug(f"File event: {event.event_type} - {event.src_path}")

    def _file_info(self, fpath: Path) -> Dict[str, Any]:
        """Get file info dict."""
        stat = fpath.stat()
        return {
            "name": fpath.name,
            "path": str(fpath),
            "relative_path": str(fpath.relative_to(Path.cwd())) if fpath.is_relative_to(Path.cwd()) else str(fpath),
            "type": "directory" if fpath.is_dir() else "file",
            "size": stat.st_size if fpath.is_file() else None,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "extension": fpath.suffix if fpath.is_file() else "",
            "permissions": oct(stat.st_mode)[-3:],
        }