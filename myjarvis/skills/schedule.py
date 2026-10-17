"""
MyJarvis — Schedule Skill
Cron, timers, reminders, recurring tasks
"""
from __future__ import annotations

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from myjarvis.skills.registry import Skill

logger = logging.getLogger(__name__)


class ScheduleSkill(Skill):
    """Scheduling: cron jobs, timers, reminders, recurring tasks."""

    name = "schedule"
    description = "Schedule: cron, timers, reminders, recurring tasks"
    version = "1.0.0"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        super().__init__(jarvis, config)
        self._register_actions()
        self._tasks: Dict[str, Dict] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._storage_path = Path("~/.myjarvis/schedule.json").expanduser()
        self._load_tasks()

    def _register_actions(self) -> None:
        self.register_action("add_cron", self.add_cron)
        self.register_action("add_timer", self.add_timer)
        self.register_action("add_reminder", self.add_reminder)
        self.register_action("list", self.list_tasks)
        self.register_action("remove", self.remove_task)
        self.register_action("enable", self.enable_task)
        self.register_action("disable", self.disable_task)
        self.register_action("run_now", self.run_now)

    def _load_tasks(self) -> None:
        """Load tasks from storage."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._tasks = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schedule: {e}")

    def _save_tasks(self) -> None:
        """Save tasks to storage."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._tasks, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save schedule: {e}")

    def add_cron(
        self,
        expression: str,
        action: str,
        skill: str = "",
        kwargs: Dict = None,
        name: str = "",
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Add a cron job. Expression: '0 9 * * 1-5' (min hour day month dow)."""
        try:
            # Validate cron expression (basic)
            parts = expression.split()
            if len(parts) != 5:
                return {"success": False, "error": "Cron expression must have 5 parts: min hour day month dow"}

            task_id = str(uuid.uuid4())[:8]
            task = {
                "id": task_id,
                "type": "cron",
                "expression": expression,
                "action": action,
                "skill": skill,
                "kwargs": kwargs or {},
                "name": name or f"cron_{task_id}",
                "enabled": enabled,
                "created": datetime.now().isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_cron(expression),
            }
            self._tasks[task_id] = task
            self._save_tasks()
            return {"success": True, "task": task}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_timer(
        self,
        seconds: float,
        action: str,
        skill: str = "",
        kwargs: Dict = None,
        name: str = "",
        repeat: bool = False,
    ) -> Dict[str, Any]:
        """Add a one-shot or repeating timer."""
        try:
            task_id = str(uuid.uuid4())[:8]
            task = {
                "id": task_id,
                "type": "timer",
                "seconds": seconds,
                "action": action,
                "skill": skill,
                "kwargs": kwargs or {},
                "name": name or f"timer_{task_id}",
                "repeat": repeat,
                "enabled": True,
                "created": datetime.now().isoformat(),
                "next_run": (datetime.now() + timedelta(seconds=seconds)).isoformat(),
            }
            self._tasks[task_id] = task
            self._save_tasks()
            return {"success": True, "task": task}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_reminder(
        self,
        at: str,  # ISO format datetime
        message: str,
        name: str = "",
    ) -> Dict[str, Any]:
        """Add a one-time reminder at specific datetime."""
        try:
            target = datetime.fromisoformat(at.replace("Z", "+00:00"))
            now = datetime.now()
            if target <= now:
                return {"success": False, "error": "Reminder time must be in the future"}

            seconds = (target - now).total_seconds()
            return self.add_timer(
                seconds=seconds,
                action="notify",
                skill="system",
                kwargs={"message": message, "title": "Reminder"},
                name=name or f"reminder_{target.strftime('%Y%m%d_%H%M')}",
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_tasks(self, enabled_only: bool = False) -> Dict[str, Any]:
        """List all scheduled tasks."""
        tasks = []
        for task in self._tasks.values():
            if enabled_only and not task.get("enabled", True):
                continue
            tasks.append(task)
        return {"success": True, "tasks": tasks, "count": len(tasks)}

    def remove_task(self, task_id: str) -> Dict[str, Any]:
        """Remove a task."""
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task {task_id} not found"}
        del self._tasks[task_id]
        self._save_tasks()
        return {"success": True, "removed": task_id}

    def enable_task(self, task_id: str, enabled: bool = True) -> Dict[str, Any]:
        """Enable/disable a task."""
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task {task_id} not found"}
        self._tasks[task_id]["enabled"] = enabled
        self._save_tasks()
        return {"success": True, "task": self._tasks[task_id]}

    def run_now(self, task_id: str) -> Dict[str, Any]:
        """Run a task immediately."""
        if task_id not in self._tasks:
            return {"success": False, "error": f"Task {task_id} not found"}

        task = self._tasks[task_id]
        try:
            result = self._execute_task(task)
            task["last_run"] = datetime.now().isoformat()
            if task["type"] == "cron":
                task["next_run"] = self._calculate_next_cron(task["expression"])
            elif task["type"] == "timer" and task.get("repeat"):
                task["next_run"] = (datetime.now() + timedelta(seconds=task["seconds"])).isoformat()
            self._save_tasks()
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_task(self, task: Dict) -> Any:
        """Execute a task action."""
        action = task["action"]
        skill_name = task.get("skill")
        kwargs = task.get("kwargs", {})

        if skill_name and self.jarvis and self.jarvis.skills:
            return self.jarvis.execute_skill(skill_name, action, **kwargs)
        elif action == "notify":
            # Built-in notification
            import plyer
            plyer.notification.notify(
                title=kwargs.get("title", "MyJarvis"),
                message=kwargs.get("message", ""),
                timeout=10,
            )
            return {"notified": True}
        else:
            return {"error": f"No skill '{skill_name}' for action '{action}'"}

    def _calculate_next_cron(self, expression: str) -> str:
        """Calculate next run time for cron expression (simplified)."""
        # This is a simplified version - for production use croniter
        try:
            from croniter import croniter
            now = datetime.now()
            cron = croniter(expression, now)
            return cron.get_next(datetime).isoformat()
        except ImportError:
            # Fallback: assume daily at the time specified
            parts = expression.split()
            hour = int(parts[1]) if parts[1].isdigit() else 9
            minute = int(parts[0]) if parts[0].isdigit() else 0
            next_run = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= datetime.now():
                next_run += timedelta(days=1)
            return next_run.isoformat()

    def start_scheduler(self) -> Dict[str, Any]:
        """Start the background scheduler."""
        if self._running:
            return {"success": False, "error": "Scheduler already running"}
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        return {"success": True, "started": True}

    def stop_scheduler(self) -> Dict[str, Any]:
        """Stop the background scheduler."""
        if not self._running:
            return {"success": False, "error": "Scheduler not running"}
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        return {"success": True, "stopped": True}

    async def _scheduler_loop(self) -> None:
        """Background loop checking for due tasks."""
        while self._running:
            try:
                now = datetime.now()
                for task in list(self._tasks.values()):
                    if not task.get("enabled", True):
                        continue
                    next_run_str = task.get("next_run")
                    if not next_run_str:
                        continue
                    try:
                        next_run = datetime.fromisoformat(next_run_str.replace("Z", "+00:00"))
                    except Exception:
                        continue

                    if next_run <= now:
                        # Execute task
                        result = self._execute_task(task)
                        task["last_run"] = now.isoformat()

                        if task["type"] == "cron":
                            task["next_run"] = self._calculate_next_cron(task["expression"])
                        elif task["type"] == "timer" and task.get("repeat"):
                            task["next_run"] = (now + timedelta(seconds=task["seconds"])).isoformat()
                        else:
                            # One-shot timer - disable
                            task["enabled"] = False

                        self._save_tasks()
                        logger.info(f"Executed scheduled task: {task['name']} ({task['id']})")

            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            await asyncio.sleep(10)  # Check every 10 seconds