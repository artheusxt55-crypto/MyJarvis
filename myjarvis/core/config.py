"""
MyJarvis — Core configuration loader
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openjarvis.core.config import load_config as oj_load_config, JarvisConfig
from openjarvis.core.paths import get_config_dir as oj_get_config_dir


def get_myjarvis_dir() -> Path:
    """Resolve MyJarvis config directory: ~/.myjarvis (or env override)."""
    env_home = os.environ.get("MYJARVIS_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    # Default to ~/.myjarvis (separate from OpenJarvis ~/.openjarvis)
    return (Path.home() / ".myjarvis").resolve()


def get_config_path() -> Path:
    """Path to myjarvis config.toml."""
    return get_myjarvis_dir() / "config.toml"


def load_config(config_path: Path | None = None) -> JarvisConfig:
    """Load MyJarvis configuration with OpenJarvis base + our overrides."""
    # Set env so OpenJarvis uses our directory
    if config_path:
        os.environ["OPENJARVIS_HOME"] = str(config_path.parent)
    else:
        os.environ["OPENJARVIS_HOME"] = str(get_myjarvis_dir())

    # Load OpenJarvis config (will read from our directory)
    config = oj_load_config()

    # Apply MyJarvis-specific overrides from our config.toml
    if config_path or (get_myjarvis_dir() / "config.toml").exists():
        _apply_myjarvis_overrides(config, config_path or get_config_path())

    return config


def _apply_myjarvis_overrides(config: JarvisConfig, config_path: Path) -> None:
    """Apply MyJarvis-specific config overrides."""
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Intelligence overrides
    if "intelligence" in data:
        intel = data["intelligence"]
        if "preferred_engine" in intel:
            config.intelligence.preferred_engine = intel["preferred_engine"]
        if "default_model" in intel:
            config.intelligence.default_model = intel["default_model"]
        if "fallback_model" in intel:
            config.intelligence.fallback_model = intel["fallback_model"]
        if "temperature" in intel:
            config.intelligence.temperature = intel["temperature"]
        if "max_tokens" in intel:
            config.intelligence.max_tokens = intel["max_tokens"]
        if "top_p" in intel:
            config.intelligence.top_p = intel.get("top_p", 0.9)
        if "engine_config" in intel:
            # Store for custom engine factory on the config object itself
            config.myjarvis_engine_config = intel["engine_config"]

    # Memory overrides
    if "memory" in data:
        mem = data["memory"]
        if "default_backend" in mem:
            config.memory.default_backend = mem["default_backend"]
        if "db_path" in mem:
            config.memory.db_path = mem["db_path"]
        if "embedding_model" in mem:
            config.myjarvis_embedding_model = mem["embedding_model"]
        if "embedding_device" in mem:
            config.myjarvis_embedding_device = mem["embedding_device"]

    # Agent overrides
    if "agent" in data:
        agent = data["agent"]
        if "default_agent" in agent:
            config.agent.default_agent = agent["default_agent"]
        if "max_turns" in agent:
            config.agent.max_turns = agent["max_turns"]
        if "default_system_prompt" in agent:
            config.agent.default_system_prompt = agent["default_system_prompt"]

    # Daemon config stored in custom attribute
    config.myjarvis_daemon = data.get("daemon", {})
    config.myjarvis_ipc = data.get("ipc", {})
    config.myjarvis_skills = data.get("skills", {})
    config.myjarvis_speech = data.get("speech", {})

    # Memory files
    if "memory_files" in data:
        mf = data["memory_files"]
        config.myjarvis_memory_files_enabled = mf.get("enabled", True)
        config.myjarvis_memory_files_soul_path = mf.get("soul_path", "~/.myjarvis/SOUL.md")
        config.myjarvis_memory_files_memory_path = mf.get("memory_path", "~/.myjarvis/MEMORY.md")
        config.myjarvis_memory_files_user_path = mf.get("user_path", "~/.myjarvis/USER.md")
        config.myjarvis_memory_files_auto_update = mf.get("auto_update", True)

    # System prompt builder
    if "system_prompt" in data:
        sp = data["system_prompt"]
        config.myjarvis_system_prompt_enabled = sp.get("enabled", True)
        config.myjarvis_system_prompt_include_soul = sp.get("include_soul", True)
        config.myjarvis_system_prompt_include_memory = sp.get("include_memory", True)
        config.myjarvis_system_prompt_include_user = sp.get("include_user", True)
        config.myjarvis_system_prompt_include_skills = sp.get("include_skills", True)
        config.myjarvis_system_prompt_include_datetime = sp.get("include_datetime", True)
        config.myjarvis_system_prompt_include_hardware = sp.get("include_hardware", True)


# Export the same interface as OpenJarvis
__all__ = ["load_config", "get_config_path", "get_myjarvis_dir", "JarvisConfig"]