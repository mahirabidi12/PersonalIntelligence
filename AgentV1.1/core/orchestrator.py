import asyncio
import logging

from browser_use import BrowserSession

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
        self.browser_session: BrowserSession | None = None
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

        # 3. Launch browser session (keep_alive prevents reset between Agent runs)
        self.browser_session = BrowserSession(
            headless=config.HEADLESS,
            keep_alive=True,
        )
        logger.info(f"Browser launched (headless={config.HEADLESS})")

        # 4. Subscribe to events
        self.event_bus.subscribe("ORDER_REQUESTED", self._handle_order_request)
        self.event_bus.subscribe("ORDER_COMPLETED", self._handle_order_complete)
        self.event_bus.subscribe("ORDER_FAILED", self._handle_order_failed)

        # 5. Create and start WhatsApp agent
        self.whatsapp_agent = WhatsAppAgent(
            browser_session=self.browser_session,
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
        """Spawn BlinkItAgent with its OWN browser session (separate from WhatsApp)."""
        item = payload.get("item", "")
        if not item:
            logger.warning("ORDER_REQUESTED with no item")
            return

        logger.info(f"=== Order requested: {item} ===")
        await self.memory.log_action("Orchestrator", "order_requested", item)

        # Pause WhatsApp polling while BlinkIt runs to save LLM calls
        if self.whatsapp_agent:
            self.whatsapp_agent._running = False
            logger.info("Paused WhatsApp polling during order")

        # Create a SEPARATE browser session for BlinkIt so it doesn't
        # fight with WhatsApp over navigation
        blinkit_session = BrowserSession(
            headless=config.HEADLESS,
            keep_alive=True,
        )
        logger.info("Created separate browser session for BlinkIt agent")

        self.blinkit_agent = BlinkItAgent(
            browser_session=blinkit_session,
            event_bus=self.event_bus,
            memory=self.memory,
            intent_detector=self.intent_detector,
        )

        # Run BlinkIt ordering, then cleanup and resume WhatsApp
        self._blinkit_task = asyncio.create_task(
            self._run_blinkit_order(item, blinkit_session)
        )
        logger.info(f"BlinkIt agent spawned for: {item} (separate browser)")

    async def _run_blinkit_order(self, item: str, blinkit_session: BrowserSession):
        """Run the BlinkIt order flow, then cleanup session and resume WhatsApp."""
        try:
            await self.blinkit_agent.run(item=item)
        except Exception as e:
            logger.error(f"BlinkIt order task failed: {e}")
        finally:
            # Kill the BlinkIt browser session
            try:
                await blinkit_session.kill()
                logger.info("BlinkIt browser session closed")
            except Exception:
                pass

            # Resume WhatsApp polling
            if self.whatsapp_agent:
                self.whatsapp_agent._running = True
                self._whatsapp_task = asyncio.create_task(self.whatsapp_agent.run())
                logger.info("Resumed WhatsApp polling after order")

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
        if self.browser_session:
            await self.browser_session.kill()

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
