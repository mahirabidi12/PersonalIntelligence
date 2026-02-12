import logging
from abc import ABC, abstractmethod

from browser_use import Browser

from core.memory import Memory
from events.bus import EventBus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, browser: Browser, event_bus: EventBus, memory: Memory):
        self.name = name
        self.browser = browser
        self.event_bus = event_bus
        self.memory = memory
        self.status: str = "idle"
        self.current_action: str | None = None

    @abstractmethod
    async def setup(self):
        """Initialize agent: navigate to site, login, etc."""
        pass

    @abstractmethod
    async def run(self):
        """Main execution loop or task."""
        pass

    async def teardown(self):
        """Cleanup resources."""
        self.status = "stopped"
        logger.info(f"[{self.name}] Teardown complete")

    async def log(self, action: str, input_data: str = "", output_data: str = "", status: str = "ok"):
        """Log an action to memory."""
        await self.memory.log_action(self.name, action, input_data, output_data, status)
        logger.info(f"[{self.name}] {action}: {status}")

    def set_status(self, status: str, action: str | None = None):
        """Update agent status."""
        self.status = status
        self.current_action = action
        logger.info(f"[{self.name}] Status: {status}" + (f" | Action: {action}" if action else ""))
