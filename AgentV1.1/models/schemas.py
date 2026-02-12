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


class FoodOption(BaseModel):
    name: str
    price: str
    description: Optional[str] = None
    element_index: int = 0


class OrderDecision(BaseModel):
    chosen_index: int
    reason: str


class Event(BaseModel):
    event_type: str
    payload: dict
    timestamp: datetime = datetime.now()


class AgentStatus(BaseModel):
    agent_name: str
    status: str = "idle"  # "running" | "idle" | "error"
    current_action: Optional[str] = None
    last_update: datetime = datetime.now()
