import asyncio
import logging
import os
import sys

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from core.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="PersonalIntelligence Agent", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator
orchestrator: Orchestrator | None = None


@app.on_event("startup")
async def startup_event():
    """Auto-start the orchestrator when the server starts."""
    global orchestrator
    orchestrator = Orchestrator()
    try:
        await orchestrator.start()
        logger.info("Orchestrator auto-started on server startup")
    except Exception as e:
        logger.error(f"Failed to auto-start orchestrator: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop orchestrator on server shutdown."""
    global orchestrator
    if orchestrator:
        await orchestrator.stop()


@app.get("/")
async def root():
    return {
        "name": "PersonalIntelligence Agent v1.1",
        "status": "running",
        "whatsapp_url": config.WHATSAPP_URL,
        "blinkit_url": config.BLINKIT_URL,
        "agent_user": config.WHATSAPP_AGENT_USER,
        "target_contact": config.WHATSAPP_TARGET_CONTACT,
        "initial_instruction": config.INITIAL_INSTRUCTION,
        "price_cap": orchestrator.supermemory.get_price_cap() if orchestrator else None,
    }


@app.get("/status")
async def get_status():
    """Get status of all agents."""
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}
    return orchestrator.get_status()


@app.post("/stop")
async def stop():
    """Stop the orchestrator."""
    global orchestrator
    if orchestrator:
        await orchestrator.stop()
        return {"status": "stopped"}
    return {"error": "Orchestrator not running"}


@app.post("/restart")
async def restart():
    """Restart the orchestrator."""
    global orchestrator
    if orchestrator:
        await orchestrator.stop()
    orchestrator = Orchestrator()
    await orchestrator.start()
    return {"status": "restarted"}


@app.post("/order")
async def trigger_order(body: dict):
    """Directly trigger an order (for testing/demo). Body: {"item": "Hot Chocolate"}"""
    if not orchestrator:
        return {"error": "Orchestrator not running"}
    item = body.get("item", "")
    if not item:
        return {"error": "No item specified"}
    await orchestrator.event_bus.publish("ORDER_REQUESTED", {"item": item})
    return {"status": "order_requested", "item": item}


@app.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent agent activity logs."""
    if not orchestrator:
        return {"error": "Orchestrator not running"}
    logs = await orchestrator.memory.get_recent_logs(limit)
    return {"logs": logs}


@app.get("/messages")
async def get_messages(limit: int = 20):
    """Get recent conversation messages."""
    if not orchestrator:
        return {"error": "Orchestrator not running"}
    messages = await orchestrator.memory.get_recent_messages(limit)
    return {"messages": [m.model_dump() for m in messages]}


@app.get("/supermemory")
async def get_supermemory():
    """Get the current supermemory content."""
    if not orchestrator:
        return {"error": "Orchestrator not running"}
    return {
        "content": orchestrator.supermemory.get_personality_prompt(),
        "price_cap": orchestrator.supermemory.get_price_cap(),
    }


@app.post("/supermemory/reload")
async def reload_supermemory():
    """Reload supermemory from disk (after you edit supermemory.md)."""
    if not orchestrator:
        return {"error": "Orchestrator not running"}
    orchestrator.supermemory.reload()
    return {
        "status": "reloaded",
        "price_cap": orchestrator.supermemory.get_price_cap(),
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  PersonalIntelligence Agent v1.1")
    print("=" * 60)
    print(f"  WhatsApp URL  : {config.WHATSAPP_URL}")
    print(f"  BlinkeyIt URL : {config.BLINKIT_URL}")
    print(f"  Agent (You)   : {config.WHATSAPP_AGENT_USER}")
    print(f"  Chatting with : {config.WHATSAPP_TARGET_CONTACT}")
    print(f"  Headless      : {config.HEADLESS}")
    print(f"  Poll Interval : {config.POLL_INTERVAL}s")
    print("-" * 60)
    print(f"  Instruction   : {config.INITIAL_INSTRUCTION[:80]}...")
    print(f"  SuperMemory   : {config.SUPERMEMORY_PATH}")
    print("=" * 60)
    print("  API: http://localhost:8000")
    print("  Endpoints:")
    print("    GET  /status            - Agent statuses")
    print("    GET  /logs              - Activity logs")
    print("    GET  /messages          - Chat messages")
    print("    GET  /supermemory       - View supermemory")
    print("    POST /order             - Trigger order: {\"item\": \"...\"}")
    print("    POST /supermemory/reload- Reload supermemory.md")
    print("    POST /stop              - Stop orchestrator")
    print("    POST /restart           - Restart orchestrator")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
