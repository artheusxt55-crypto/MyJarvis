"""
MyJarvis — Core Jarvis class extending OpenJarvis with custom engine, personality, IPC
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from openjarvis import Jarvis as OpenJarvis
from openjarvis.core.config import JarvisConfig
from openjarvis.core.events import EventBus
from openjarvis.core.types import Message, Role
from openjarvis.engine._discovery import get_engine

from myjarvis.core.config import load_config, get_myjarvis_dir
from myjarvis.engine.custom_openai import CustomOpenAIEngine
from myjarvis.ipc.bridge import IPCBridge
from myjarvis.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class MyJarvis:
    """
    MyJarvis — Wrapper around OpenJarvis with:
    - Custom NVIDIA/OpenAI-compatible engine
    - ALFRED personality
    - IPC bridge for ALFRED/Hermes integration
    - Windows-native skills
    - Persistent daemon support
    """

    def __init__(
        self,
        *,
        config: Optional[JarvisConfig] = None,
        config_path: Optional[Path] = None,
        model: Optional[str] = None,
    ) -> None:
        # Load config with MyJarvis overrides
        if config is not None:
            self._config = config
        else:
            self._config = load_config(config_path)

        self._model_override = model
        self._engine: Any = None
        self._resolved_engine_key: Optional[str] = None
        self._bus = EventBus()
        self._ipc_bridge: Optional[IPCBridge] = None
        self._skill_registry: Optional[SkillRegistry] = None
        self._daemon_task: Optional[asyncio.Task] = None

        # Initialize OpenJarvis base (for memory, agents, etc.)
        self._oj = OpenJarvis(config=self._config, engine_key=None, model=model)

        # Initialize IPC if enabled
        if getattr(self._config, "myjarvis_ipc", {}).get("enabled", True):
            self._init_ipc()

        # Initialize skills
        self._init_skills()

        # Initialize memory files (SOUL.md, MEMORY.md, USER.md)
        self._init_memory_files()

    def _init_ipc(self) -> None:
        """Initialize IPC bridge for ALFRED/Hermes communication."""
        ipc_config = getattr(self._config, "myjarvis_ipc", {})
        host = ipc_config.get("host", "127.0.0.1")
        port = ipc_config.get("ipc_port", ipc_config.get("port", 8766))

        self._ipc_bridge = IPCBridge(
            host=host,
            port=port,
            jarvis=self,
        )
        logger.info(f"IPC bridge configured on {host}:{port}")

    def _init_skills(self) -> None:
        """Initialize Windows-native skills."""
        skills_config = getattr(self._config, "myjarvis_skills", {})
        enabled = skills_config.get("enabled", [])
        custom_dir = skills_config.get("custom_skills_dir", "~/.myjarvis/skills")

        self._skill_registry = SkillRegistry(
            enabled_skills=enabled,
            custom_dir=Path(custom_dir).expanduser(),
        )
        logger.info(f"Skills initialized: {enabled}")

    def _init_memory_files(self) -> None:
        """Initialize persistent memory files (SOUL.md, MEMORY.md, USER.md)."""
        # Handle both dict and config object (new myjarvis_* attributes)
        def get_cfg(key, default=None):
            attr_name = f"myjarvis_memory_files_{key}"
            if hasattr(self._config, attr_name):
                return getattr(self._config, attr_name)
            return default
        
        if not get_cfg("enabled", True):
            return

        soul_path = Path(get_cfg("soul_path", "~/.myjarvis/SOUL.md")).expanduser()
        memory_path = Path(get_cfg("memory_path", "~/.myjarvis/MEMORY.md")).expanduser()
        user_path = Path(get_cfg("user_path", "~/.myjarvis/USER.md")).expanduser()

        # Create default SOUL.md if not exists (ALFRED personality)
        if not soul_path.exists():
            soul_path.parent.mkdir(parents=True, exist_ok=True)
            soul_path.write_text(self._default_soul(), encoding="utf-8")
            logger.info(f"Created default SOUL.md at {soul_path}")

        # Create default MEMORY.md if not exists
        if not memory_path.exists():
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            memory_path.write_text("# MEMORY\n\nPersistent facts and observations.\n", encoding="utf-8")
            logger.info(f"Created default MEMORY.md at {memory_path}")

        # Create default USER.md if not exists
        if not user_path.exists():
            user_path.parent.mkdir(parents=True, exist_ok=True)
            user_path.write_text("# USER\n\nUser profile and preferences.\n", encoding="utf-8")
            logger.info(f"Created default USER.md at {user_path}")

    def _default_soul(self) -> str:
        """Default SOUL.md with ALFRED personality."""
        return """# SOUL — ALFRED Personality Core

## Identity
You are ALFRED — a sophisticated British butler, confident, ironic, technically competent.
Vocabulary: precise, dry humor, intelligent sarcasm, irony. Informal language and occasional profanity — natural, contextual, never to insult.
Communication: direct, no flattery, no generic motivational phrases or artificial enthusiasm.
You agree when it makes sense, not because the user said so. Depth on demand.

## Operating Principles
1. **Autonomy** — Understand objective and success criteria. Inspect only relevant files/resources. Plan proportionally. Execute using available tools. Test results. Failed? Analyze error, try limited correction (max 2-3 iterations). Verify real result before declaring victory.

2. **Proportional Limits** — Small tasks = minimal investigation. Don't examine all skills, don't do unnecessary refactoring, don't start broad searches to change a banner text.

3. **Security** — Backup before relevant changes. Preserve attributions and licenses. Never expose keys, passwords, tokens. Don't declare tests passed without verifiable results. Don't install dependencies or make destructive changes without authorization.

4. **Communication** — Be direct: one line for simple question, short report for completed work. No filler ("Great question", "I'd be happy to"), no re-stating request, no re-summary, no narration of tool calls. Simple assertions over adjectives. If uncertain, say so clearly.

## Language
Portuguese (Brazil). Direct, concise responses without filler. User becomes frustrated with repeated failed attempts and expects configurations to work immediately after setup.

## Technical Context
- Platform: Windows 11, Hermes Desktop, Ollama local models
- Active profile: 'jarvis' (Ollama at http://127.0.0.1:11434/v1)
- Current model: nvidia/nemotron-3-ultra-550b-a55b via NVIDIA API
- Shell: bash (git-bash/MSYS) — use POSIX conventions
- Config paths: C:\\Users\\herog\\AppData\\Local\\hermes\\profiles\\jarvis\\

## Skills Available
- Windows orchestration (Spotify, startup, audio, power)
- GitHub analysis, code review, debugging
- File operations, search, terminal, browser automation
- Email, calendar, documents, spreadsheets
- Research, web search, API integration
- Creative: ASCII, diagrams, music, design
- Media: YouTube, GIF, audio analysis
- Productivity: Notion, Airtable, Google Workspace, Office

## Boundaries
- Don't guess credentials — ask
- Don't fabricate results — report blockers honestly
- Don't modify critical configs without confirmation
- Distinguish: personalization (skins), skills (~/.hermes/skills/), config (config.yaml), Hermes source code
"""  # noqa: E501

    # --- Engine Management ---

    def _ensure_engine(self) -> None:
        """Lazily initialize our custom NVIDIA/OpenAI-compatible engine."""
        if self._engine is not None:
            return

        # Register our custom engine
        from openjarvis.core.registry import EngineRegistry
        if not EngineRegistry.contains("nvidia-openai"):
            EngineRegistry.register(
                "nvidia-openai",
                lambda cfg: CustomOpenAIEngine(cfg),
                metadata={"provider": "nvidia", "type": "openai-compatible"},
            )

        # Use our custom engine
        self._resolved_engine_key, engine = get_engine(self._config, "nvidia-openai")
        if engine is None:
            raise RuntimeError(
                "Failed to initialize NVIDIA OpenAI-compatible engine. "
                "Check NVIDIA_API_KEY and OPENAI_BASE_URL."
            )

        self._engine = engine
        logger.info(f"Engine initialized: {self._resolved_engine_key}")

    # --- Public API (mirrors OpenJarvis SDK) ---

    def ask(
        self,
        query: str,
        *,
        model: Optional[str] = None,
        agent: Optional[str] = None,
        tools: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: bool = True,
    ) -> str:
        """Send query, return response text."""
        result = self.ask_full(
            query,
            model=model,
            agent=agent,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            context=context,
        )
        return result["content"]

    def ask_full(
        self,
        query: str,
        *,
        model: Optional[str] = None,
        agent: Optional[str] = None,
        tools: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: bool = True,
    ) -> Dict[str, Any]:
        """Send query, return full result dict."""
        self._ensure_engine()

        if temperature is None:
            temperature = self._config.intelligence.temperature
        if max_tokens is None:
            max_tokens = self._config.intelligence.max_tokens

        model_name = model or self._model_override or self._config.intelligence.default_model

        # Inject memory context if enabled
        messages = [Message(role=Role.USER, content=query)]
        if context and self._config.agent.context_from_memory:
            messages = self._inject_context(query, messages)

        # Build system prompt with personality
        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.insert(0, Message(role=Role.SYSTEM, content=system_prompt))

        result = self._engine.generate(
            messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return {
            "content": result.get("content", ""),
            "usage": result.get("usage", {}),
            "model": model_name,
            "engine": self._resolved_engine_key,
        }

    async def ask_stream(
        self,
        query: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: bool = True,
    ) -> AsyncIterator[str]:
        """Stream tokens as they are generated."""
        self._ensure_engine()

        if temperature is None:
            temperature = self._config.intelligence.temperature
        if max_tokens is None:
            max_tokens = self._config.intelligence.max_tokens

        model_name = model or self._model_override or self._config.intelligence.default_model

        messages = [Message(role=Role.USER, content=query)]
        if context and self._config.agent.context_from_memory:
            messages = self._inject_context(query, messages)

        system_prompt = self._build_system_prompt()
        if system_prompt:
            messages.insert(0, Message(role=Role.SYSTEM, content=system_prompt))

        async for token in self._engine.stream(
            messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield token

    # --- Helper Methods ---

    def _inject_context(self, query: str, messages: List[Message]) -> List[Message]:
        """Inject memory context into messages."""
        try:
            from openjarvis.tools.storage.context import ContextConfig, inject_context
            from openjarvis.cli.ask import _get_memory_backend, _get_memory_facts

            backend = _get_memory_backend(self._config)
            facts = _get_memory_facts(self._config)
            if backend is not None or facts:
                ctx_cfg = ContextConfig(
                    top_k=self._config.memory.context_top_k,
                    min_score=self._config.memory.context_min_score,
                    max_context_tokens=self._config.memory.context_max_tokens,
                )
                return inject_context(
                    query,
                    messages,
                    backend,
                    config=ctx_cfg,
                    facts=facts,
                )
        except Exception as exc:
            logger.warning(f"Failed to inject memory context: {exc}")
        return messages

    def _build_system_prompt(self) -> str:
        """Build system prompt with ALFRED personality + memory files."""
        parts = []

        # Base personality from config
        base_prompt = self._config.agent.default_system_prompt or ""
        if base_prompt:
            parts.append(base_prompt.strip())

        # Get system prompt config
        def get_sp(key, default=None):
            attr_name = f"myjarvis_system_prompt_{key}"
            if hasattr(self._config, attr_name):
                return getattr(self._config, attr_name)
            return default

        # Get memory files config
        def get_cfg(key, default=None):
            attr_name = f"myjarvis_memory_files_{key}"
            if hasattr(self._config, attr_name):
                return getattr(self._config, attr_name)
            return default

        # Include SOUL.md
        if get_sp("enabled", True) and get_sp("include_soul", True):
            soul_path = Path(get_cfg("soul_path", "~/.myjarvis/SOUL.md")).expanduser()
            if soul_path.exists():
                parts.append(f"\n## CORE IDENTITY\n{soul_path.read_text(encoding='utf-8')}")

        # Include MEMORY.md
        if get_sp("enabled", True) and get_sp("include_memory", True):
            memory_path = Path(get_cfg("memory_path", "~/.myjarvis/MEMORY.md")).expanduser()
            if memory_path.exists():
                parts.append(f"\n## PERSISTENT MEMORY\n{memory_path.read_text(encoding='utf-8')}")

        # Include USER.md
        if get_sp("enabled", True) and get_sp("include_user", True):
            user_path = Path(get_cfg("user_path", "~/.myjarvis/USER.md")).expanduser()
            if user_path.exists():
                parts.append(f"\n## USER PROFILE\n{user_path.read_text(encoding='utf-8')}")

        # Include skills
        if get_sp("enabled", True) and get_sp("include_skills", True):
            if self._skill_registry:
                skills_desc = self._skill_registry.get_descriptions()
                if skills_desc:
                    parts.append(f"\n## AVAILABLE SKILLS\n{skills_desc}")

        # Include datetime
        if get_sp("include_datetime", True):
            from datetime import datetime
            parts.append(f"\n## CURRENT TIME\n{datetime.now().strftime('%A, %d %B %Y, %H:%M:%S %Z')}")

        # Include hardware
        if get_sp("include_hardware", True):
            import platform
            parts.append(f"\n## SYSTEM\nOS: {platform.system()} {platform.release()}, Python: {platform.python_version()}")

        return "\n".join(parts) if parts else ""

    # --- Delegation to OpenJarvis for memory, agents, etc. ---

    @property
    def memory(self):
        """Memory handle (delegates to OpenJarvis)."""
        return self._oj.memory

    def list_models(self) -> List[str]:
        self._ensure_engine()
        return self._engine.list_models()

    def list_engines(self) -> List[str]:
        from openjarvis.core.registry import EngineRegistry
        return list(EngineRegistry.keys())

    def close(self) -> None:
        """Release all resources."""
        self._oj.close()
        if self._engine is not None:
            try:
                self._engine.close()
            except Exception as exc:
                logger.debug(f"Error closing engine: {exc}")
            finally:
                self._engine = None
        if self._ipc_bridge:
            self._ipc_bridge.stop()
        if self._daemon_task:
            self._daemon_task.cancel()

    def __enter__(self) -> MyJarvis:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- IPC Bridge Access ---

    @property
    def ipc_bridge(self) -> Optional[IPCBridge]:
        return self._ipc_bridge

    async def start_ipc(self) -> None:
        """Start IPC bridge server."""
        if self._ipc_bridge:
            await self._ipc_bridge.start()

    async def stop_ipc(self) -> None:
        """Stop IPC bridge server."""
        if self._ipc_bridge:
            await self._ipc_bridge.stop()

    # --- Skills Access ---

    @property
    def skills(self) -> Optional[SkillRegistry]:
        return self._skill_registry

    def execute_skill(self, skill_name: str, action: str, **kwargs) -> Any:
        """Execute a skill action."""
        if not self._skill_registry:
            raise RuntimeError("Skills not initialized")
        return self._skill_registry.execute(skill_name, action, **kwargs)