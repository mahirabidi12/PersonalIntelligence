import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import config
from core.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentV1.2 - Browser Intelligence Agent", version="1.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

orchestrator: Orchestrator | None = None
ws_connections: list[WebSocket] = []


# ---- WebSocket broadcast helper ----
async def broadcast_to_ws(event: dict):
    dead = []
    for ws in ws_connections:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_connections.remove(ws)


# ---- Lifecycle ----
@app.on_event("startup")
async def startup():
    global orchestrator
    orchestrator = Orchestrator()
    try:
        await orchestrator.start()
        orchestrator.event_bus.add_ws_listener(broadcast_to_ws)
        logger.info("Orchestrator auto-started")
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {e}")


@app.on_event("shutdown")
async def shutdown():
    if orchestrator:
        await orchestrator.stop()


# ---- API Endpoints ----
@app.get("/")
async def dashboard():
    """Serve the web dashboard."""
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "dashboard.html")
    with open(ui_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/status")
async def get_status():
    if not orchestrator:
        return {"error": "Not initialized"}
    return orchestrator.get_status()


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    if not orchestrator:
        return {"error": "Not initialized"}
    logs = await orchestrator.memory.get_recent_logs(limit)
    return {"logs": logs}


@app.get("/api/messages")
async def get_messages(limit: int = 30):
    if not orchestrator:
        return {"error": "Not initialized"}
    msgs = await orchestrator.memory.get_recent_messages(limit)
    return {"messages": [m.model_dump() for m in msgs]}


@app.get("/api/tasks")
async def get_tasks(limit: int = 20):
    if not orchestrator:
        return {"error": "Not initialized"}
    tasks = await orchestrator.memory.get_tasks(limit)
    return {"tasks": tasks}


@app.get("/api/events")
async def get_events():
    if not orchestrator:
        return {"error": "Not initialized"}
    return {"events": orchestrator.event_bus.event_log[-50:]}


@app.get("/api/supermemory")
async def get_supermemory():
    if not orchestrator:
        return {"error": "Not initialized"}
    return {
        "content": orchestrator.supermemory.get_personality_prompt(),
        "price_cap": orchestrator.supermemory.get_price_cap(),
    }


@app.get("/api/config")
async def get_config():
    return {
        "whatsapp_url": config.WHATSAPP_URL,
        "blinkit_url": config.BLINKIT_URL,
        "agent_user": config.WHATSAPP_AGENT_USER,
        "target_contact": config.WHATSAPP_TARGET_CONTACT,
        "poll_interval": config.POLL_INTERVAL,
        "headless": config.HEADLESS,
        "llm_model": config.LLM_MODEL,
    }


# ---- Action Endpoints ----
class TaskBody(BaseModel):
    task_type: str = "browse"
    description: str
    url: str = ""
    params: dict = {}


@app.post("/api/task")
async def submit_task(body: TaskBody):
    if not orchestrator:
        return {"error": "Not initialized"}
    task_id = await orchestrator.submit_task(
        body.task_type, body.description, body.url, body.params
    )
    return {"task_id": task_id, "status": "submitted"}


@app.post("/api/whatsapp/start")
async def start_whatsapp():
    if not orchestrator:
        return {"error": "Not initialized"}
    try:
        await orchestrator.start_whatsapp()
        return {"status": "started"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/order")
async def trigger_order(body: dict):
    if not orchestrator:
        return {"error": "Not initialized"}
    item = body.get("item", "")
    if not item:
        return {"error": "No item specified"}
    await orchestrator.event_bus.publish("ORDER_REQUESTED", {"item": item})
    return {"status": "order_requested", "item": item}


@app.post("/api/stop")
async def stop_agent():
    if orchestrator:
        await orchestrator.stop()
    return {"status": "stopped"}


@app.post("/api/restart")
async def restart_agent():
    global orchestrator
    if orchestrator:
        await orchestrator.stop()
    orchestrator = Orchestrator()
    await orchestrator.start()
    orchestrator.event_bus.add_ws_listener(broadcast_to_ws)
    return {"status": "restarted"}


@app.post("/api/supermemory/reload")
async def reload_supermemory():
    if not orchestrator:
        return {"error": "Not initialized"}
    orchestrator.supermemory.reload()
    return {"status": "reloaded", "price_cap": orchestrator.supermemory.get_price_cap()}


# ---- WebSocket for live updates ----
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_connections.append(ws)
    logger.info(f"WebSocket client connected ({len(ws_connections)} total)")
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # Handle ping
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in ws_connections:
            ws_connections.remove(ws)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AgentV1.2 — Browser Intelligence Agent")
    print("=" * 60)
    print(f"  WhatsApp URL  : {config.WHATSAPP_URL}")
    print(f"  Blinkit URL   : {config.BLINKIT_URL}")
    print(f"  Agent User    : {config.WHATSAPP_AGENT_USER}")
    print(f"  Target Contact: {config.WHATSAPP_TARGET_CONTACT}")
    print(f"  LLM Model     : {config.LLM_MODEL}")
    print(f"  Headless      : {config.HEADLESS}")
    print(f"  Poll Interval : {config.POLL_INTERVAL}s")
    print("-" * 60)
    print(f"  Dashboard: http://localhost:{config.AGENT_PORT}")
    print(f"  WebSocket: ws://localhost:{config.AGENT_PORT}/ws")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=config.AGENT_PORT)
