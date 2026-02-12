import asyncio
import json
import logging

from browser_use import Agent, Browser
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from config import config
from core.intent import IntentDetector
from core.memory import Memory
from events.bus import EventBus
from models.schemas import ChatMessage

logger = logging.getLogger(__name__)


class WhatsAppAgent(BaseAgent):
    """
    V1.2 WhatsApp Agent — Improved with:
    - Better message extraction (more robust parsing)
    - Automatic retry on failures
    - Pending notification queue for order updates
    - Configurable polling interval
    """

    def __init__(self, browser: Browser, event_bus: EventBus, memory: Memory, intent_detector: IntentDetector):
        super().__init__("WhatsAppAgent", browser, event_bus, memory)
        self.intent_detector = intent_detector
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)
        self.last_messages: list[str] = []
        self._pending_notifications: list[str] = []

        self.event_bus.subscribe("ORDER_COMPLETED", self._on_order_completed)
        self.event_bus.subscribe("ORDER_FAILED", self._on_order_failed)

    async def _on_order_completed(self, payload: dict):
        item = payload.get("item", "your order")
        self._pending_notifications.append(f"ordered it baby! your {item} is on its way")
        logger.info(f"[WhatsApp] Queued order notification: {item}")

    async def _on_order_failed(self, payload: dict):
        item = payload.get("item", "that")
        error = payload.get("error", "something went wrong")
        self._pending_notifications.append(f"sorry babe, couldn't order {item} right now — {error}")

    async def setup(self):
        self.set_status("running", "Logging into WhatsApp")
        await self.log("setup_start", f"Navigating to {config.WHATSAPP_URL}")

        # Login via quick-login button
        login_agent = Agent(
            task=f"""
            Go to {config.WHATSAPP_URL}
            You'll see a login page. Find and click the "Quick Login" button for "{config.WHATSAPP_AGENT_USER}"
            (or fill email "{config.WHATSAPP_LOGIN_EMAIL}" and password "{config.WHATSAPP_LOGIN_PASSWORD}" and click Login).
            Wait for the chat interface to load.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await login_agent.run()
        await asyncio.sleep(2)

        # Click target contact
        contact_agent = Agent(
            task=f"""
            In the sidebar contact list on the left, find and click on "{config.WHATSAPP_TARGET_CONTACT}" to open their chat.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await contact_agent.run()
        await self.log("setup_complete", f"Chat opened with {config.WHATSAPP_TARGET_CONTACT}")

    async def run(self, **kwargs):
        self._running = True
        self.set_status("running", "Polling for messages")

        while self._running:
            try:
                await self._send_pending_notifications()
                new_messages = await self._check_for_new_messages()

                if new_messages:
                    await self.log("new_messages", f"{len(new_messages)} new: {new_messages}")

                    for msg in new_messages:
                        await self.memory.save_message("user", msg, config.WHATSAPP_TARGET_CONTACT)

                    recent = await self.memory.get_recent_messages(limit=20)
                    intent_result = await self.intent_detector.detect(recent)

                    await self.log("intent_detected", f"{intent_result.intent}: {intent_result.reply}")

                    if intent_result.reply:
                        await self._send_message(intent_result.reply)
                        await self.memory.save_message("agent", intent_result.reply, config.WHATSAPP_AGENT_USER)

                    if intent_result.intent == "order_food" and intent_result.item:
                        await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})

            except Exception as e:
                logger.error(f"[WhatsApp] Poll error: {e}")
                await self.log("error", str(e), status="error")

            await asyncio.sleep(config.POLL_INTERVAL)

    async def _check_for_new_messages(self) -> list[str]:
        try:
            extract_agent = Agent(
                task="""
                Look at the chat messages area. Extract ALL visible messages as a JSON array.
                Each: {"sender": "Name", "text": "message content"}
                Return ONLY the JSON array.
                """,
                llm=self.llm,
                browser=self.browser,
            )
            result = await extract_agent.run()
            result_text = result.final_result() if hasattr(result, 'final_result') else str(result)
            messages = self._parse_messages(result_text)

            new_msgs = []
            for msg in messages:
                text = msg.get("text", "").strip()
                sender = msg.get("sender", "").strip()
                if text and sender == config.WHATSAPP_TARGET_CONTACT and text not in self.last_messages:
                    new_msgs.append(text)

            self.last_messages = [m.get("text", "") for m in messages]
            return new_msgs
        except Exception as e:
            logger.error(f"[WhatsApp] Message extraction failed: {e}")
            return []

    def _parse_messages(self, text: str) -> list[dict]:
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    async def _send_message(self, text: str):
        try:
            send_agent = Agent(
                task=f"""
                Find the message input field at the bottom of the chat. Click it, type exactly:
                {text}
                Then press Enter to send.
                """,
                llm=self.llm,
                browser=self.browser,
            )
            await send_agent.run()
            await self.log("sent_message", text)
        except Exception as e:
            logger.error(f"[WhatsApp] Send failed: {e}")

    async def _send_pending_notifications(self):
        while self._pending_notifications:
            msg = self._pending_notifications.pop(0)
            await self._send_message(msg)
            await self.memory.save_message("agent", msg, config.WHATSAPP_AGENT_USER)
