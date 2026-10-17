"""
MyJarvis — Web UI (FastAPI + HTMX + Tailwind)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis

logger = logging.getLogger(__name__)

# Global Jarvis instance
jarvis_instance: Optional[MyJarvis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global jarvis_instance
    logger.info("Starting MyJarvis Web UI...")
    config = load_config()
    jarvis_instance = MyJarvis(config=config)
    
    # Start IPC bridge
    await jarvis_instance.start_ipc()
    
    logger.info("MyJarvis ready!")
    yield
    
    logger.info("Shutting down...")
    await jarvis_instance.stop_ipc()
    jarvis_instance.close()


app = FastAPI(
    title="MyJarvis Web UI",
    description="ALFRED Personality Assistant Web Interface",
    version="1.0.0",
    lifespan=lifespan,
)

# Templates and static
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    model: Optional[str] = None
    stream: bool = False
    context: bool = True


class SkillRequest(BaseModel):
    skill: str
    action: str
    kwargs: Dict[str, Any] = {}


# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


manager = ConnectionManager()


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status")
async def get_status():
    if not jarvis_instance:
        return JSONResponse({"status": "stopped"})
    
    return {
        "status": "running",
        "engine": jarvis_instance._resolved_engine_key,
        "model": jarvis_instance._config.intelligence.default_model,
        "skills": list(jarvis_instance.skills.skills.keys()) if jarvis_instance.skills else [],
        "ipc_clients": len(jarvis_instance.ipc_bridge._clients) if jarvis_instance.ipc_bridge else 0,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not jarvis_instance:
        return JSONResponse({"error": "Jarvis not initialized"}, status_code=503)
    
    try:
        if request.stream:
            async def event_stream():
                async for token in jarvis_instance.ask_stream(
                    request.query,
                    model=request.model,
                    context=request.context,
                ):
                    yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(event_stream(), media_type="text/event-stream")
        else:
            response = jarvis_instance.ask(
                request.query,
                model=request.model,
                context=request.context,
            )
            return {"response": response}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/skill")
async def execute_skill(request: SkillRequest):
    if not jarvis_instance or not jarvis_instance.skills:
        return JSONResponse({"error": "Skills not available"}, status_code=503)
    
    try:
        result = jarvis_instance.execute_skill(request.skill, request.action, **request.kwargs)
        return {"result": result}
    except Exception as e:
        logger.error(f"Skill error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/skills")
async def list_skills():
    if not jarvis_instance or not jarvis_instance.skills:
        return {"skills": []}
    
    skills_info = {}
    for name, skill in jarvis_instance.skills.skills.items():
        skills_info[name] = {
            "description": skill.description,
            "actions": list(skill.get_actions().keys()),
        }
    return {"skills": skills_info}


@app.get("/api/memory")
async def get_memory():
    if not jarvis_instance:
        return {"soul": "", "memory": "", "user": ""}
    
    def read_file(path_attr: str) -> str:
        path = Path(getattr(jarvis_instance._config, f"myjarvis_memory_files_{path_attr}", f"~/.myjarvis/{path_attr.upper()}.md")).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    
    return {
        "soul": read_file("soul_path"),
        "memory": read_file("memory_path"),
        "user": read_file("user_path"),
    }


@app.post("/api/memory")
async def update_memory(request: Request):
    data = await request.json()
    section = data.get("section")
    content = data.get("content", "")
    
    if section not in ["soul", "memory", "user"]:
        return JSONResponse({"error": "Invalid section"}, status_code=400)
    
    path = Path(getattr(jarvis_instance._config, f"myjarvis_memory_files_{section}_path", f"~/.myjarvis/{section.upper()}.md")).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    
    return {"success": True}


@app.get("/api/config")
async def get_config():
    if not jarvis_instance:
        return {}
    
    config = jarvis_instance._config
    return {
        "intelligence": {
            "preferred_engine": config.intelligence.preferred_engine,
            "default_model": config.intelligence.default_model,
            "temperature": config.intelligence.temperature,
            "max_tokens": config.intelligence.max_tokens,
        },
        "skills": {
            "enabled": getattr(config, "myjarvis_skills", {}).get("enabled", []),
        },
        "daemon": getattr(config, "myjarvis_daemon", {}),
        "ipc": getattr(config, "myjarvis_ipc", {}),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "chat":
                query = msg.get("query", "")
                async for token in jarvis_instance.ask_stream(query):
                    await websocket.send_text(json.dumps({"type": "token", "token": token}))
                await websocket.send_text(json.dumps({"type": "done"}))
            
            elif msg.get("type") == "skill":
                skill = msg.get("skill")
                action = msg.get("action")
                kwargs = msg.get("kwargs", {})
                try:
                    result = jarvis_instance.execute_skill(skill, action, **kwargs)
                    await websocket.send_text(json.dumps({"type": "skill_result", "result": result}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)