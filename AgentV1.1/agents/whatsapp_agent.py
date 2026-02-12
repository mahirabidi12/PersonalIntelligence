import asyncio
import json
import logging

from browser_use import Agent, BrowserSession
from browser_use.llm.models import ChatOpenAI

from agents.base_agent import BaseAgent
from config import config
from core.intent import IntentDetector
from core.memory import Memory
from events.bus import EventBus
from models.schemas import ChatMessage

logger = logging.getLogger(__name__)


class WhatsAppAgent(BaseAgent):
    """
    WhatsApp chat agent. Runs continuously:
    - Polls the WhatsApp clone UI for new messages
    - Sends messages to LLM for intent detection
    - Replies as the girlfriend persona
    - Publishes ORDER_REQUESTED when food craving detected
    """

    def __init__(self, browser_session: BrowserSession, event_bus: EventBus, memory: Memory, intent_detector: IntentDetector):
        super().__init__("WhatsAppAgent", browser_session, event_bus, memory)
        self.intent_detector = intent_detector
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)
        self.last_message_count = 0
        self.last_messages: list[str] = []
        self._running = False
        self._pending_notifications: list[str] = []

        # Subscribe to order events
        self.event_bus.subscribe("ORDER_COMPLETED", self._on_order_completed)
        self.event_bus.subscribe("ORDER_FAILED", self._on_order_failed)

    async def _on_order_completed(self, payload: dict):
        """Queue a confirmation message to send in WhatsApp."""
        item = payload.get("item", "your order")
        self._pending_notifications.append(
            f"ordered it baby! your {item} is on its way 🎉"
        )
        logger.info(f"[WhatsAppAgent] Queued order completion notification for: {item}")

    async def _on_order_failed(self, payload: dict):
        """Queue a failure message to send in WhatsApp."""
        item = payload.get("item", "that")
        error = payload.get("error", "something went wrong")
        self._pending_notifications.append(
            f"sorry babe, couldn't order {item} right now 😔 {error}"
        )
        logger.info(f"[WhatsAppAgent] Queued order failure notification for: {item}")

    async def setup(self):
        """Navigate to WhatsApp, login as agent user, open target contact chat."""
        self.set_status("running", "Setting up WhatsApp")

        # Single setup agent: navigate, select user, and open target contact
        setup_agent = Agent(
            task=f"""
            Go to {config.WHATSAPP_URL}
            You will see a "Pick a User" screen with radio buttons. Select "{config.WHATSAPP_AGENT_USER}" (the one labeled "User 1" or "{config.WHATSAPP_USER_ID}").
            Click the "Enter Chat" button to log in.
            Then in the contacts list on the left, find and click on "{config.WHATSAPP_TARGET_CONTACT}".
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await setup_agent.run()
        await self.log("setup", f"Navigated to WhatsApp and opened chat with {config.WHATSAPP_TARGET_CONTACT}")

        logger.info(f"[WhatsAppAgent] Setup complete. Chatting as {config.WHATSAPP_AGENT_USER} with {config.WHATSAPP_TARGET_CONTACT}")

    async def run(self):
        """Main polling loop: check for new messages, detect intent, reply."""
        self._running = True
        self.set_status("running", "Polling for messages")

        while self._running:
            try:
                # Send any pending notifications first
                await self._send_pending_notifications()

                # Extract current messages from the chat UI
                new_messages = await self._check_for_new_messages()

                if new_messages:
                    logger.info(f"[WhatsAppAgent] Found {len(new_messages)} new message(s)")

                    # Save new messages to memory
                    for msg in new_messages:
                        await self.memory.save_message("user", msg, config.WHATSAPP_TARGET_CONTACT)

                    # Get full conversation context and detect intent
                    recent = await self.memory.get_recent_messages(limit=20)
                    intent_result = await self.intent_detector.detect(recent)

                    await self.log(
                        "intent_detected",
                        json.dumps({"messages": new_messages}),
                        json.dumps({"intent": intent_result.intent, "reply": intent_result.reply, "item": intent_result.item}),
                    )

                    # Send reply (strip newlines to avoid sending multiple messages)
                    if intent_result.reply:
                        reply_text = intent_result.reply.replace("\n", " ").strip()
                        await self._send_message(reply_text)
                        await self.memory.save_message("agent", reply_text, config.WHATSAPP_AGENT_USER)

                    # If food intent, publish order event
                    if intent_result.intent == "order_food" and intent_result.item:
                        await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})
                        logger.info(f"[WhatsAppAgent] Published ORDER_REQUESTED for: {intent_result.item}")

            except Exception as e:
                logger.error(f"[WhatsAppAgent] Error in polling loop: {e}")
                await self.log("error", str(e), status="error")

            await asyncio.sleep(config.POLL_INTERVAL)

    async def _check_for_new_messages(self) -> list[str]:
        """Use browser-use to extract messages and find new ones."""
        try:
            extract_agent = Agent(
                task=f"""
                Look at the OPEN CHAT conversation only (the right-side message area, NOT the left sidebar contact list).
                Extract ONLY the last 5 messages from this conversation as a JSON array.
                Each message should have "sender" (either "{config.WHATSAPP_AGENT_USER}" or "{config.WHATSAPP_TARGET_CONTACT}") and "text".
                IGNORE the sidebar contact previews completely.
                Return ONLY the JSON array, nothing else.
                Example: [{{"sender": "{config.WHATSAPP_AGENT_USER}", "text": "hello"}}, {{"sender": "{config.WHATSAPP_TARGET_CONTACT}", "text": "hi!"}}]
                """,
                llm=self.llm,
                browser_session=self.browser_session,
                use_judge=False,
            )
            result = await extract_agent.run()

            # Parse the result - browser-use returns AgentHistoryList
            result_text = result.final_result() if hasattr(result, 'final_result') else str(result)

            # Try to extract JSON from the result
            messages = self._parse_messages(result_text)

            # Find new messages by comparing with what we've seen
            new_messages = []
            current_texts = [m.get("text", "") for m in messages]

            for msg in messages:
                text = msg.get("text", "").strip()
                sender = msg.get("sender", "").strip()
                # Only consider messages from the target contact that we haven't seen
                if text and sender == config.WHATSAPP_TARGET_CONTACT and text not in self.last_messages:
                    new_messages.append(text)

            self.last_messages = current_texts
            return new_messages

        except Exception as e:
            logger.error(f"[WhatsAppAgent] Failed to extract messages: {e}")
            return []

    def _parse_messages(self, text: str) -> list[dict]:
        """Try to parse JSON message array from browser-use output."""
        if not text:
            return []

        # Clean up: strip whitespace, remove markdown code fences, remove judge notes
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        # Remove simple judge appended text like "\n\n[Simple judge: ...]"
        if "\n\n[Simple judge:" in cleaned:
            cleaned = cleaned.split("\n\n[Simple judge:")[0]
        cleaned = cleaned.strip()

        # Try direct JSON parse
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Find the JSON array by matching brackets from the first [
        start = cleaned.find("[")
        if start >= 0:
            depth = 0
            for i in range(start, len(cleaned)):
                if cleaned[i] == "[":
                    depth += 1
                elif cleaned[i] == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(cleaned[start:i + 1])
                            if isinstance(data, list):
                                return data
                        except json.JSONDecodeError:
                            pass
                        break

        logger.warning(f"[WhatsAppAgent] Could not parse messages (len={len(text)}): {text[:300]}")
        return []

    async def _send_message(self, text: str):
        """Use browser-use to type and send a message."""
        try:
            send_agent = Agent(
                task=f"""
                In the chat area, find the message input field (usually at the bottom of the chat).
                Click on it, type the following message exactly:
                {text}
                Then press Enter or click the Send button to send the message.
                """,
                llm=self.llm,
                browser_session=self.browser_session,
                use_judge=False,
            )
            await send_agent.run()
            logger.info(f"[WhatsAppAgent] Sent message: {text}")
            await self.log("send_message", text)
        except Exception as e:
            logger.error(f"[WhatsAppAgent] Failed to send message: {e}")

    async def _send_pending_notifications(self):
        """Send any queued notification messages."""
        while self._pending_notifications:
            msg = self._pending_notifications.pop(0)
            await self._send_message(msg)
            await self.memory.save_message("agent", msg, config.WHATSAPP_AGENT_USER)

    async def teardown(self):
        """Stop the polling loop."""
        self._running = False
        await super().teardown()
