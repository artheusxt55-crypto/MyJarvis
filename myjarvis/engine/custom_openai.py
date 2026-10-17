"""
MyJarvis — Custom NVIDIA/OpenAI-compatible Engine
Uses NVIDIA API (OpenAI-compatible) for nemotron-3-ultra and other models
"""
from __future__ import annotations

import os
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from openjarvis.core.config import JarvisConfig
from openjarvis.engine._base import InferenceEngine as BaseEngine, EngineConnectionError as EngineError
from openjarvis.core.registry import EngineRegistry

logger = logging.getLogger(__name__)


# Register engine
@EngineRegistry.register("nvidia-openai")
class CustomOpenAIEngine(BaseEngine):
    """
    OpenAI-compatible engine for NVIDIA API (integrate.api.nvidia.com/v1)
    and other OpenAI-compatible endpoints (Ollama, vLLM, etc.)
    """

    def __init__(self, config: JarvisConfig = None, host: str = None) -> None:
        # InferenceEngine has no custom __init__, don't call super()
        # Handle both calling conventions: (config) or (host) from _make_engine
        if isinstance(config, str) and host is None:
            # Called as __init__(host) by _make_engine
            host = config
            config = None
        
        # InferenceEngine has no custom __init__, don't call super()
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

        # Get config from myjarvis_engine_config (set by config loader) or environment
        engine_config = getattr(config, "myjarvis_engine_config", {}) if config else {}
        
        # Priority: explicit host param > engine_config.base_url > env var > default
        if host:
            self.base_url = host
        else:
            self.base_url = engine_config.get("base_url") or os.environ.get("OPENAI_BASE_URL") or "https://integrate.api.nvidia.com/v1"
        
        self.api_key = engine_config.get("api_key") or os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.provider = engine_config.get("provider", "nvidia")

        if not self.api_key:
            raise EngineError(
                "API key not configured. Set NVIDIA_API_KEY or OPENAI_API_KEY environment variable, "
                "or configure intelligence.engine_config.api_key in config.toml"
            )

        # Default headers
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Model mapping (NVIDIA model IDs)
        self._model_map = {
            "nemotron-3-ultra": "nvidia/nemotron-3-ultra-550b-a55b",
            "nemotron-3-ultra-550b": "nvidia/nemotron-3-ultra-550b-a55b",
            "nemotron": "nvidia/nemotron-3-ultra-550b-a55b",
            "llama-3.1-70b": "meta/llama-3.1-70b-instruct",
            "llama-3.1-8b": "meta/llama-3.1-8b-instruct",
            "llama-3.3-70b": "meta/llama-3.3-70b-instruct",
            "mistral-large": "mistralai/mistral-large",
            "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
            "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
            "deepseek-r1": "deepseek-ai/deepseek-r1",
        }

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers,
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                headers=self._headers,
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._sync_client

    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full model ID."""
        return self._model_map.get(model.lower(), model)

    # --- BaseEngine Interface ---

    def list_models(self) -> List[str]:
        """Return list of available models."""
        return list(self._model_map.values()) + list(self._model_map.keys())

    def health(self) -> bool:
        """Check if the engine is healthy and available."""
        try:
            client = self._get_sync_client()
            response = client.get("/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate completion (sync)."""
        client = self._get_sync_client()
        model_id = self._resolve_model(model)

        # Convert messages to dict if they are Message objects
        serializable_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                serializable_messages.append(msg)
            else:
                # Assume it's a Message object with role and content attributes
                serializable_messages.append({
                    "role": getattr(msg, "role", "user"),
                    "content": getattr(msg, "content", ""),
                })

        payload = {
            "model": model_id,
            "messages": serializable_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }

        # Add any extra parameters
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        try:
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            if stream:
                return {"stream": data}  # Not used in sync
            else:
                choice = data["choices"][0]
                return {
                    "content": choice["message"]["content"],
                    "usage": data.get("usage", {}),
                    "model": data.get("model", model_id),
                    "finish_reason": choice.get("finish_reason"),
                }

        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise EngineError(error_msg) from e
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise EngineError(f"Generation failed: {e}") from e

    async def agenerate(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate completion (async)."""
        client = self._get_client()
        model_id = self._resolve_model(model)

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": False,
        }

        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            return {
                "content": choice["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", model_id),
                "finish_reason": choice.get("finish_reason"),
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise EngineError(error_msg) from e
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise EngineError(f"Generation failed: {e}") from e

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream tokens as they are generated."""
        client = self._get_client()
        model_id = self._resolve_model(model)

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True,
        }

        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as e:
            error_msg = f"API error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise EngineError(error_msg) from e
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise EngineError(f"Streaming failed: {e}") from e

    def close(self) -> None:
        """Close HTTP clients."""
        if self._client and not self._client.is_closed:
            self._client.close()
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()


# Register engine class (not factory) so _make_engine can instantiate it with config
# Registration is done via decorator on the class above