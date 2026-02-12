import logging
from abc import ABC, abstractmethod

from browser_use import Browser

from core.memory import Memory
from events.bus import EventBus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all V1.2 agents."""

    def __init__(self, name: str, browser: Browser, event_bus: EventBus, memory: Memory):
        self.name = name
        self.browser = browser
        self.event_bus = event_bus
        self.memory = memory
        self.status: str = "idle"
        self.current_action: str | None = None
        self._running = False

    @abstractmethod
    async def setup(self):
        pass

    @abstractmethod
    async def run(self, **kwargs):
        pass

    async def teardown(self):
        self._running = False
        self.status = "stopped"
        logger.info(f"[{self.name}] Teardown complete")

    async def log(self, action: str, detail: str = "", status: str = "ok"):
        await self.memory.log_action(self.name, action, detail, status)
        await self.event_bus.publish("AGENT_LOG", {
            "agent": self.name, "action": action, "detail": detail, "status": status
        })
        logger.info(f"[{self.name}] {action}: {detail[:100]}")

    def set_status(self, status: str, action: str | None = None):
        self.status = status
        self.current_action = action
