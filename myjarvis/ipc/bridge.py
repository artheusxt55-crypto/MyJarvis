"""
MyJarvis — IPC Bridge for ALFRED/Hermes Integration
WebSocket server that allows ALFRED/Hermes to communicate with MyJarvis daemon
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class IPCBridge:
    """
    WebSocket-based IPC bridge between ALFRED/Hermes and MyJarvis daemon.
    
    Protocol:
    - Client connects to ws://127.0.0.1:8765
    - Messages are JSON with: {id, type, payload}
    - Types: ask, ask_stream, skill, status, ping, close
    - Responses: {id, type, payload, error}
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8766,
        jarvis: Any = None,
    ) -> None:
        self.host = host
        self.port = port
        self.jarvis = jarvis
        self._server: Optional[websockets.WebSocketServer] = None
        self._clients: Dict[str, WebSocketServerProtocol] = {}
        self._handlers: Dict[str, Callable] = {
            "ask": self._handle_ask,
            "ask_stream": self._handle_ask_stream,
            "skill": self._handle_skill,
            "status": self._handle_status,
            "ping": self._handle_ping,
            "models": self._handle_models,
            "memory_search": self._handle_memory_search,
            "memory_index": self._handle_memory_index,
        }

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        )
        logger.info(f"IPC Bridge started on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        # Close all client connections
        for client_id, ws in self._clients.items():
            try:
                await ws.close(code=1001, reason="Server shutting down")
            except Exception:
                pass
        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("IPC Bridge stopped")

    async def _handle_connection(self, ws: WebSocketServerProtocol) -> None:
        """Handle new WebSocket connection."""
        client_id = str(uuid.uuid4())[:8]
        self._clients[client_id] = ws
        logger.debug(f"IPC Client connected: {client_id} ({len(self._clients)} total)")

        try:
            async for message in ws:
                await self._process_message(client_id, ws, message)
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"IPC Client {client_id} error: {e}")
        finally:
            self._clients.pop(client_id, None)
            logger.debug(f"IPC Client disconnected: {client_id} ({len(self._clients)} remaining)")

    async def _process_message(
        self,
        client_id: str,
        ws: WebSocketServerProtocol,
        message: str,
    ) -> None:
        """Process incoming message."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            await self._send_error(ws, None, f"Invalid JSON: {e}")
            return

        msg_id = data.get("id", str(uuid.uuid4())[:8])
        msg_type = data.get("type")
        payload = data.get("payload", {})

        if msg_type not in self._handlers:
            await self._send_error(ws, msg_id, f"Unknown message type: {msg_type}")
            return

        handler = self._handlers[msg_type]
        try:
            await handler(ws, msg_id, payload)
        except Exception as e:
            logger.error(f"IPC Handler {msg_type} error: {e}")
            await self._send_error(ws, msg_id, str(e))

    async def _send_response(
        self,
        ws: WebSocketServerProtocol,
        msg_id: str,
        msg_type: str,
        payload: Any,
    ) -> None:
        """Send response message."""
        response = {
            "id": msg_id,
            "type": msg_type,
            "payload": payload,
        }
        await ws.send(json.dumps(response, ensure_ascii=False))

    async def _send_error(
        self,
        ws: WebSocketServerProtocol,
        msg_id: Optional[str],
        error: str,
    ) -> None:
        """Send error response."""
        response = {
            "id": msg_id or str(uuid.uuid4())[:8],
            "type": "error",
            "payload": {"error": error},
        }
        await ws.send(json.dumps(response, ensure_ascii=False))

    # --- Message Handlers ---

    async def _handle_ask(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle ask request (non-streaming)."""
        query = payload.get("query")
        if not query:
            await self._send_error(ws, msg_id, "Missing 'query' in payload")
            return

        model = payload.get("model")
        temperature = payload.get("temperature")
        max_tokens = payload.get("max_tokens")
        context = payload.get("context", True)

        try:
            response = self.jarvis.ask(
                query,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                context=context,
            )
            await self._send_response(ws, msg_id, "ask_response", {
                "content": response,
                "model": model or self.jarvis._config.intelligence.default_model,
            })
        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    async def _handle_ask_stream(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle ask_stream request (streaming)."""
        query = payload.get("query")
        if not query:
            await self._send_error(ws, msg_id, "Missing 'query' in payload")
            return

        model = payload.get("model")
        temperature = payload.get("temperature")
        max_tokens = payload.get("max_tokens")
        context = payload.get("context", True)

        try:
            # Send start marker
            await self._send_response(ws, msg_id, "stream_start", {"model": model})

            # Stream tokens
            async for token in self.jarvis.ask_stream(
                query,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                context=context,
            ):
                await self._send_response(ws, msg_id, "stream_token", {"token": token})

            # Send end marker
            await self._send_response(ws, msg_id, "stream_end", {})

        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    async def _handle_skill(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle skill execution."""
        skill_name = payload.get("skill")
        action = payload.get("action")
        kwargs = payload.get("kwargs", {})

        if not skill_name or not action:
            await self._send_error(ws, msg_id, "Missing 'skill' or 'action'")
            return

        try:
            result = self.jarvis.execute_skill(skill_name, action, **kwargs)
            await self._send_response(ws, msg_id, "skill_response", {
                "skill": skill_name,
                "action": action,
                "result": result,
            })
        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    async def _handle_status(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle status request."""
        status = {
            "running": True,
            "engine": self.jarvis._resolved_engine_key,
            "model": self.jarvis._config.intelligence.default_model,
            "clients_connected": len(self._clients),
            "skills_loaded": list(self.jarvis._skill_registry._skills.keys()) if self.jarvis._skill_registry else [],
            "memory_stats": self.jarvis.memory.stats() if hasattr(self.jarvis, 'memory') else {},
        }
        await self._send_response(ws, msg_id, "status_response", status)

    async def _handle_ping(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle ping."""
        await self._send_response(ws, msg_id, "pong", {"timestamp": payload.get("timestamp")})

    async def _handle_models(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle list models request."""
        try:
            models = self.jarvis.list_models()
            await self._send_response(ws, msg_id, "models_response", {"models": models})
        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    async def _handle_memory_search(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle memory search."""
        query = payload.get("query")
        top_k = payload.get("top_k", 5)
        if not query:
            await self._send_error(ws, msg_id, "Missing 'query'")
            return

        try:
            results = self.jarvis.memory.search(query, top_k=top_k)
            await self._send_response(ws, msg_id, "memory_search_response", {"results": results})
        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    async def _handle_memory_index(self, ws: WebSocketServerProtocol, msg_id: str, payload: Dict) -> None:
        """Handle memory index."""
        path = payload.get("path")
        if not path:
            await self._send_error(ws, msg_id, "Missing 'path'")
            return

        try:
            result = self.jarvis.memory.index(path)
            await self._send_response(ws, msg_id, "memory_index_response", result)
        except Exception as e:
            await self._send_error(ws, msg_id, str(e))

    # --- Broadcast to all clients ---

    async def broadcast(self, msg_type: str, payload: Any) -> None:
        """Broadcast message to all connected clients."""
        if not self._clients:
            return

        message = json.dumps({
            "id": str(uuid.uuid4())[:8],
            "type": msg_type,
            "payload": payload,
        }, ensure_ascii=False)

        disconnected = []
        for client_id, ws in self._clients.items():
            try:
                await ws.send(message)
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            self._clients.pop(client_id, None)