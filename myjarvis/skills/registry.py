"""
MyJarvis — Skills Registry and Base Classes
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class Skill:
    """Base class for all MyJarvis skills."""

    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = "MyJarvis"

    def __init__(self, jarvis: Any = None, config: Dict = None):
        self.jarvis = jarvis
        self.config = config or {}
        self._actions: Dict[str, Callable] = {}

    def register_action(self, name: str, func: Callable) -> None:
        """Register an action that can be called via IPC."""
        self._actions[name] = func

    def get_actions(self) -> Dict[str, Callable]:
        """Return available actions."""
        return self._actions.copy()

    def execute(self, action: str, **kwargs) -> Any:
        """Execute an action by name."""
        if action not in self._actions:
            raise ValueError(f"Skill '{self.name}' has no action '{action}'. Available: {list(self._actions.keys())}")
        return self._actions[action](**kwargs)

    def get_description(self) -> str:
        """Return skill description with actions."""
        actions = list(self._actions.keys())
        return f"{self.description} | Actions: {', '.join(actions) if actions else 'none'}"


class SkillRegistry:
    """Registry for loading and managing skills."""

    def __init__(self, enabled_skills: List[str] = None, custom_dir: Path = None):
        self.enabled_skills = enabled_skills or []
        self.custom_dir = custom_dir or Path("~/.myjarvis/skills").expanduser()
        self._skills: Dict[str, Skill] = {}
        self._skill_classes: Dict[str, Type[Skill]] = {}

        # Built-in skill modules
        self._builtin_skills = {
            "windows_control": "myjarvis.skills.windows_control:WindowsControlSkill",
            "bluetooth": "myjarvis.skills.bluetooth:BluetoothSkill",
            "audio": "myjarvis.skills.audio:AudioSkill",
            "filesystem": "myjarvis.skills.filesystem:FileSystemSkill",
            "process": "myjarvis.skills.process:ProcessSkill",
            "network": "myjarvis.skills.network:NetworkSkill",
            "power": "myjarvis.skills.power:PowerSkill",
            "schedule": "myjarvis.skills.schedule:ScheduleSkill",
            "clipboard": "myjarvis.skills.clipboard:ClipboardSkill",
            "screenshot": "myjarvis.skills.screenshot:ScreenshotSkill",
        }

        self._load_skills()

    def _load_skills(self) -> None:
        """Load all enabled skills."""
        # Load built-in skills
        for skill_name in self.enabled_skills:
            if skill_name in self._builtin_skills:
                self._load_builtin_skill(skill_name)
            else:
                # Try custom skill
                self._load_custom_skill(skill_name)

    def _load_builtin_skill(self, skill_name: str) -> None:
        """Load a built-in skill by import path."""
        import_path = self._builtin_skills[skill_name]
        try:
            module_path, class_name = import_path.split(":")
            module = importlib.import_module(module_path)
            skill_class = getattr(module, class_name)
            self._skill_classes[skill_name] = skill_class
            logger.info(f"Loaded built-in skill: {skill_name}")
        except Exception as e:
            logger.error(f"Failed to load built-in skill {skill_name}: {e}")

    def _load_custom_skill(self, skill_name: str) -> None:
        """Load a custom skill from custom_dir."""
        skill_file = self.custom_dir / f"{skill_name}.py"
        if not skill_file.exists():
            logger.warning(f"Custom skill file not found: {skill_file}")
            return

        try:
            spec = importlib.util.spec_from_file_location(f"myjarvis_skill_{skill_name}", skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Skill subclass
            skill_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Skill) and attr is not Skill:
                    skill_class = attr
                    break

            if skill_class:
                self._skill_classes[skill_name] = skill_class
                logger.info(f"Loaded custom skill: {skill_name}")
            else:
                logger.warning(f"No Skill subclass found in {skill_file}")

        except Exception as e:
            logger.error(f"Failed to load custom skill {skill_name}: {e}")

    def get(self, skill_name: str) -> Optional[Skill]:
        """Get or create skill instance."""
        if skill_name in self._skills:
            return self._skills[skill_name]

        if skill_name not in self._skill_classes:
            return None

        skill_class = self._skill_classes[skill_name]
        try:
            instance = skill_class(jarvis=None, config={})
            self._skills[skill_name] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate skill {skill_name}: {e}")
            return None

    def execute(self, skill_name: str, action: str, **kwargs) -> Any:
        """Execute a skill action."""
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found or not loaded")
        return skill.execute(action, **kwargs)

    def get_descriptions(self) -> str:
        """Get descriptions of all loaded skills."""
        lines = []
        for name in self.enabled_skills:
            skill = self.get(name)
            if skill:
                lines.append(f"- {name}: {skill.get_description()}")
            else:
                lines.append(f"- {name}: (not loaded)")
        return "\n".join(lines)

    @property
    def skills(self) -> Dict[str, Skill]:
        """Return all loaded skill instances."""
        return self._skills.copy()

    def list_available(self) -> List[str]:
        """List all available skill names."""
        return list(self._skill_classes.keys())

    def reload(self, skill_name: str) -> bool:
        """Reload a specific skill."""
        if skill_name in self._skills:
            del self._skills[skill_name]
        if skill_name in self._skill_classes:
            del self._skill_classes[skill_name]

        if skill_name in self._builtin_skills:
            self._load_builtin_skill(skill_name)
        else:
            self._load_custom_skill(skill_name)

        return skill_name in self._skill_classes