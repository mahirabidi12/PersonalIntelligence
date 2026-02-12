from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "agent"
    content: str
    timestamp: str = ""
    sender_name: str = ""


class IntentResult(BaseModel):
    intent: str  # "normal_chat" | "order_food" | "greeting" | "order_status"
    reply: Optional[str] = None
    item: Optional[str] = None
    confidence: float = 0.0


class TaskRequest(BaseModel):
    task_type: str  # "browse" | "whatsapp" | "blinkit_order" | "custom"
    description: str
    url: Optional[str] = None
    params: dict = {}


class TaskResult(BaseModel):
    task_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    result: Optional[str] = None
    error: Optional[str] = None
    screenshots: list[str] = []
    created_at: str = ""
    completed_at: str = ""


class AgentLog(BaseModel):
    agent_name: str
    action: str
    detail: str = ""
    status: str = "ok"
    timestamp: str = ""


class Event(BaseModel):
    event_type: str
    payload: dict = {}
    timestamp: str = datetime.now().isoformat()
