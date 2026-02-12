import asyncio
import logging

from browser_use import Browser, BrowserProfile

from agents.blinkit_agent import BlinkItAgent
from agents.whatsapp_agent import WhatsAppAgent
from config import config
from core.intent import IntentDetector
from core.memory import Memory
from core.supermemory import SuperMemory
from events.bus import EventBus

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central controller. Starts the browser, initializes agents,
    manages the event loop, and coordinates between agents.
    """

    def __init__(self):
        self.browser: Browser | None = None
        self.event_bus = EventBus()
        self.memory = Memory(config.DB_PATH)
        self.supermemory = SuperMemory()
        self.intent_detector = IntentDetector(supermemory=self.supermemory)

        self.whatsapp_agent: WhatsAppAgent | None = None
        self.blinkit_agent: BlinkItAgent | None = None

        self._whatsapp_task: asyncio.Task | None = None
        self._blinkit_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Initialize everything and start the WhatsApp agent."""
        logger.info("=== Orchestrator starting ===")

        # 1. Init memory
        await self.memory.init_db()
        logger.info("Memory initialized")

        # 2. Start event bus
        await self.event_bus.start()
        logger.info("Event bus started")

        # 3. Launch browser (visible for judges)
        self.browser = Browser(
            config=BrowserProfile(
                headless=config.HEADLESS,
            )
        )
        logger.info(f"Browser launched (headless={config.HEADLESS})")

        # 4. Subscribe to events
        self.event_bus.subscribe("ORDER_REQUESTED", self._handle_order_request)
        self.event_bus.subscribe("ORDER_COMPLETED", self._handle_order_complete)
        self.event_bus.subscribe("ORDER_FAILED", self._handle_order_failed)

        # 5. Create and start WhatsApp agent
        self.whatsapp_agent = WhatsAppAgent(
            browser=self.browser,
            event_bus=self.event_bus,
            memory=self.memory,
            intent_detector=self.intent_detector,
        )

        await self.whatsapp_agent.setup()
        self._whatsapp_task = asyncio.create_task(self.whatsapp_agent.run())
        self._running = True

        logger.info("=== Orchestrator running ===")
        logger.info(f"WhatsApp agent: chatting as {config.WHATSAPP_AGENT_USER} with {config.WHATSAPP_TARGET_CONTACT}")
        logger.info(f"WhatsApp URL: {config.WHATSAPP_URL}")
        logger.info(f"BlinkeyIt URL: {config.BLINKIT_URL}")

    async def _handle_order_request(self, payload: dict):
        """Spawn BlinkItAgent as a non-blocking async task."""
        item = payload.get("item", "")
        if not item:
            logger.warning("ORDER_REQUESTED with no item")
            return

        logger.info(f"=== Order requested: {item} ===")
        await self.memory.log_action("Orchestrator", "order_requested", item)

        # Create BlinkIt agent and run it in background
        self.blinkit_agent = BlinkItAgent(
            browser=self.browser,
            event_bus=self.event_bus,
            memory=self.memory,
            intent_detector=self.intent_detector,
        )

        # CRITICAL: asyncio.create_task — does NOT block the chat loop
        self._blinkit_task = asyncio.create_task(self.blinkit_agent.run(item=item))
        logger.info(f"BlinkIt agent spawned for: {item} (non-blocking)")

    async def _handle_order_complete(self, payload: dict):
        """Log order completion."""
        item = payload.get("item", "")
        logger.info(f"=== Order completed: {item} ===")
        await self.memory.log_action("Orchestrator", "order_completed", item)

    async def _handle_order_failed(self, payload: dict):
        """Log order failure."""
        item = payload.get("item", "")
        error = payload.get("error", "unknown")
        logger.error(f"=== Order failed: {item} | {error} ===")
        await self.memory.log_action("Orchestrator", "order_failed", f"{item}: {error}", status="error")

    async def stop(self):
        """Gracefully shut down everything."""
        logger.info("=== Orchestrator stopping ===")
        self._running = False

        # Stop agents
        if self.whatsapp_agent:
            await self.whatsapp_agent.teardown()
        if self._whatsapp_task:
            self._whatsapp_task.cancel()
            try:
                await self._whatsapp_task
            except asyncio.CancelledError:
                pass

        if self.blinkit_agent:
            await self.blinkit_agent.teardown()
        if self._blinkit_task and not self._blinkit_task.done():
            self._blinkit_task.cancel()
            try:
                await self._blinkit_task
            except asyncio.CancelledError:
                pass

        # Stop event bus
        await self.event_bus.stop()

        # Close browser
        if self.browser:
            await self.browser.close()

        logger.info("=== Orchestrator stopped ===")

    def get_status(self) -> dict:
        """Get current status of all agents."""
        status = {
            "orchestrator": "running" if self._running else "stopped",
            "whatsapp_agent": {
                "status": self.whatsapp_agent.status if self.whatsapp_agent else "not_created",
                "action": self.whatsapp_agent.current_action if self.whatsapp_agent else None,
            },
            "blinkit_agent": {
                "status": self.blinkit_agent.status if self.blinkit_agent else "not_created",
                "action": self.blinkit_agent.current_action if self.blinkit_agent else None,
            },
        }
        return status
