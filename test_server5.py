
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    config = load_config()
    jarvis = MyJarvis(config=config)
    print("MyJarvis created")
    yield
    print("Shutting down...")
    jarvis.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return HTMLResponse("<h1>Test OK</h1>")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
