import asyncio
import logging
import uuid

from browser_use import Browser, BrowserProfile

from agents.blinkit_agent import BlinkItAgent
from agents.browser_agent import BrowserTaskAgent
from agents.whatsapp_agent import WhatsAppAgent
from config import config
from core.intent import IntentDetector
from core.memory import Memory
from core.supermemory import SuperMemory
from events.bus import EventBus

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    V1.2 Orchestrator — Central controller with:
    - Task queue for general browser tasks
    - WhatsApp + Blinkit agent management
    - WebSocket event broadcasting
    - Screenshot management
    """

    def __init__(self):
        self.browser: Browser | None = None
        self.event_bus = EventBus()
        self.memory = Memory(config.DB_PATH)
        self.supermemory = SuperMemory()
        self.intent_detector = IntentDetector(supermemory=self.supermemory)

        self.whatsapp_agent: WhatsAppAgent | None = None
        self.blinkit_agent: BlinkItAgent | None = None
        self.browser_task_agent: BrowserTaskAgent | None = None

        self._whatsapp_task: asyncio.Task | None = None
        self._blinkit_task: asyncio.Task | None = None
        self._browser_tasks: list[asyncio.Task] = []
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        logger.info("=== Orchestrator V1.2 starting ===")

        await self.memory.init_db()
        await self.event_bus.start()

        # Launch headless browser
        self.browser = Browser(config=BrowserProfile(headless=config.HEADLESS))
        logger.info(f"Browser launched (headless={config.HEADLESS})")

        # Subscribe to events
        self.event_bus.subscribe("ORDER_REQUESTED", self._handle_order_request)
        self.event_bus.subscribe("ORDER_COMPLETED", self._handle_order_complete)
        self.event_bus.subscribe("ORDER_FAILED", self._handle_order_failed)

        # Create browser task agent
        self.browser_task_agent = BrowserTaskAgent(
            browser=self.browser, event_bus=self.event_bus, memory=self.memory
        )

        self._running = True
        logger.info("=== Orchestrator V1.2 running ===")

    async def start_whatsapp(self):
        """Initialize and start WhatsApp agent."""
        if self.whatsapp_agent:
            await self.whatsapp_agent.teardown()

        self.whatsapp_agent = WhatsAppAgent(
            browser=self.browser,
            event_bus=self.event_bus,
            memory=self.memory,
            intent_detector=self.intent_detector,
        )
        await self.whatsapp_agent.setup()
        self._whatsapp_task = asyncio.create_task(self.whatsapp_agent.run())
        logger.info(f"WhatsApp agent started: {config.WHATSAPP_AGENT_USER} -> {config.WHATSAPP_TARGET_CONTACT}")

    async def submit_task(self, task_type: str, description: str, url: str = "", params: dict = None) -> str:
        """Submit a task to the agent. Returns task_id."""
        task_id = f"task-{str(uuid.uuid4())[:8]}"
        await self.memory.save_task(task_id, task_type, description)

        if task_type == "blinkit_order":
            item = (params or {}).get("item", description)
            await self.event_bus.publish("ORDER_REQUESTED", {"item": item, "task_id": task_id})
        elif task_type == "whatsapp":
            if not self.whatsapp_agent:
                await self.start_whatsapp()
        else:
            # General browser task
            await self.memory.update_task(task_id, "running")
            task = asyncio.create_task(
                self.browser_task_agent.run(task_id=task_id, description=description, url=url)
            )
            self._browser_tasks.append(task)

        await self.event_bus.publish("TASK_SUBMITTED", {"task_id": task_id, "type": task_type, "description": description})
        return task_id

    async def _handle_order_request(self, payload: dict):
        item = payload.get("item", "")
        if not item:
            return

        logger.info(f"Order requested: {item}")
        await self.memory.log_action("Orchestrator", "order_requested", item)

        self.blinkit_agent = BlinkItAgent(
            browser=self.browser,
            event_bus=self.event_bus,
            memory=self.memory,
            intent_detector=self.intent_detector,
        )
        self._blinkit_task = asyncio.create_task(self.blinkit_agent.run(item=item))

    async def _handle_order_complete(self, payload: dict):
        item = payload.get("item", "")
        logger.info(f"Order completed: {item}")
        await self.memory.log_action("Orchestrator", "order_completed", item)

    async def _handle_order_failed(self, payload: dict):
        item = payload.get("item", "")
        error = payload.get("error", "unknown")
        logger.error(f"Order failed: {item} | {error}")
        await self.memory.log_action("Orchestrator", "order_failed", f"{item}: {error}", "error")

    async def stop(self):
        logger.info("=== Orchestrator stopping ===")
        self._running = False

        if self.whatsapp_agent:
            await self.whatsapp_agent.teardown()
        if self._whatsapp_task:
            self._whatsapp_task.cancel()
            try: await self._whatsapp_task
            except asyncio.CancelledError: pass

        if self.blinkit_agent:
            await self.blinkit_agent.teardown()
        if self._blinkit_task and not self._blinkit_task.done():
            self._blinkit_task.cancel()
            try: await self._blinkit_task
            except asyncio.CancelledError: pass

        for t in self._browser_tasks:
            if not t.done():
                t.cancel()

        await self.event_bus.stop()
        if self.browser:
            await self.browser.close()

        logger.info("=== Orchestrator stopped ===")

    def get_status(self) -> dict:
        return {
            "orchestrator": "running" if self._running else "stopped",
            "whatsapp_agent": {
                "status": self.whatsapp_agent.status if self.whatsapp_agent else "not_started",
                "action": self.whatsapp_agent.current_action if self.whatsapp_agent else None,
            },
            "blinkit_agent": {
                "status": self.blinkit_agent.status if self.blinkit_agent else "not_started",
                "action": self.blinkit_agent.current_action if self.blinkit_agent else None,
            },
            "browser_task_agent": {
                "status": self.browser_task_agent.status if self.browser_task_agent else "not_started",
                "action": self.browser_task_agent.current_action if self.browser_task_agent else None,
            },
            "pending_tasks": self._task_queue.qsize(),
        }
