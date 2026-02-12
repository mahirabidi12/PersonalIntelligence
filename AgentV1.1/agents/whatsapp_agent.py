import asyncio
import json
import logging

from supabase import create_client

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
    - Polls Supabase directly for new messages (no browser scraping)
    - Sends messages to LLM for intent detection
    - Replies by inserting into Supabase (instant, no browser agent)
    - Publishes ORDER_REQUESTED when food craving detected
    - Browser is only used for initial setup (login + open chat) so user can watch
    """

    def __init__(self, browser_session: BrowserSession, event_bus: EventBus, memory: Memory, intent_detector: IntentDetector):
        super().__init__("WhatsAppAgent", browser_session, event_bus, memory)
        self.intent_detector = intent_detector
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)
        self._running = False
        self._ordering = False
        self._pending_notifications: list[str] = []

        # Supabase client for direct DB access
        self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)

        # Conversation ID: sorted user IDs + "-chat"
        ids = sorted([config.WHATSAPP_USER_ID, config.WHATSAPP_TARGET_ID])
        self.conversation_id = f"{ids[0]}-{ids[1]}-chat"

        # Track the last message timestamp we've seen to detect new ones
        self._last_seen_ts: str | None = None

        # Subscribe to order events
        self.event_bus.subscribe("ORDER_COMPLETED", self._on_order_completed)
        self.event_bus.subscribe("ORDER_FAILED", self._on_order_failed)

    async def _on_order_completed(self, payload: dict):
        """Queue a confirmation message to send in WhatsApp."""
        self._ordering = False
        item = payload.get("item", "your order")
        self._pending_notifications.append(
            f"ordered it baby! your {item} is on its way 🎉"
        )
        logger.info(f"[WhatsAppAgent] Queued order completion notification for: {item}")

    async def _on_order_failed(self, payload: dict):
        """Queue a failure message to send in WhatsApp."""
        self._ordering = False
        item = payload.get("item", "that")
        error = payload.get("error", "something went wrong")
        self._pending_notifications.append(
            f"sorry babe, couldn't order {item} right now 😔 {error}"
        )
        logger.info(f"[WhatsAppAgent] Queued order failure notification for: {item}")

    async def setup(self):
        """Navigate to WhatsApp, login as agent user, open target contact chat."""
        self.set_status("running", "Setting up WhatsApp")

        # Browser setup: navigate, select user, and open target contact (visual only)
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

        # Load last 5 messages into memory for context, and reply if latest is from Ananya
        await self._bootstrap_conversation()

        logger.info(f"[WhatsAppAgent] Setup complete. Chatting as {config.WHATSAPP_AGENT_USER} with {config.WHATSAPP_TARGET_CONTACT}")
        logger.info(f"[WhatsAppAgent] Conversation ID: {self.conversation_id}")
        logger.info(f"[WhatsAppAgent] Using Supabase for message read/write (no browser scraping)")

    async def _bootstrap_conversation(self):
        """Load last 5 messages into memory. If the latest is from the target, reply immediately."""
        result = (
            self.supabase.table("chats")
            .select("sender_id, content, created_at")
            .eq("conversation_id", self.conversation_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        if not result.data:
            self._last_seen_ts = None
            logger.info("[WhatsAppAgent] No existing messages in conversation")
            return

        # Messages come newest-first, reverse for chronological order
        messages = list(reversed(result.data))

        # Save all 5 into memory for LLM context
        for msg in messages:
            sender_id = msg["sender_id"]
            if sender_id == config.WHATSAPP_TARGET_ID:
                role = "user"
                name = config.WHATSAPP_TARGET_CONTACT
            else:
                role = "agent"
                name = config.WHATSAPP_AGENT_USER
            await self.memory.save_message(role, msg["content"], name)

        # Set last_seen_ts to the latest message timestamp
        self._last_seen_ts = messages[-1]["created_at"]
        logger.info(f"[WhatsAppAgent] Loaded {len(messages)} messages into memory")
        logger.info(f"[WhatsAppAgent] Last message timestamp: {self._last_seen_ts}")

        # If the latest message is from the target contact, reply now
        latest = messages[-1]
        if latest["sender_id"] == config.WHATSAPP_TARGET_ID:
            logger.info(f"[WhatsAppAgent] Latest message is from {config.WHATSAPP_TARGET_CONTACT}: \"{latest['content']}\" — replying immediately")

            recent = await self.memory.get_recent_messages(limit=20)
            intent_result = await self.intent_detector.detect(recent)

            await self.log(
                "intent_detected",
                json.dumps({"messages": [latest["content"]]}),
                json.dumps({"intent": intent_result.intent, "reply": intent_result.reply, "item": intent_result.item}),
            )

            if intent_result.reply:
                reply_text = intent_result.reply.replace("\n", " ").strip()
                await self._send_message(reply_text)
                await self.memory.save_message("agent", reply_text, config.WHATSAPP_AGENT_USER)

            if intent_result.intent == "order_food" and intent_result.item and not self._ordering:
                self._ordering = True
                await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})
                logger.info(f"[WhatsAppAgent] Published ORDER_REQUESTED for: {intent_result.item}")
        else:
            logger.info(f"[WhatsAppAgent] Latest message is from us — waiting for {config.WHATSAPP_TARGET_CONTACT}")

    async def run(self):
        """Main polling loop: check Supabase for new messages, detect intent, reply."""
        self._running = True
        self.set_status("running", "Polling for messages via Supabase")

        while self._running:
            try:
                # Send any pending notifications first
                await self._send_pending_notifications()

                # Check Supabase for new messages from target contact
                new_messages = await self._check_for_new_messages()

                if new_messages:
                    logger.info(f"[WhatsAppAgent] Found {len(new_messages)} new message(s) from {config.WHATSAPP_TARGET_CONTACT}")

                    # Save new messages to memory
                    for msg_text in new_messages:
                        await self.memory.save_message("user", msg_text, config.WHATSAPP_TARGET_CONTACT)

                    # Get full conversation context and detect intent
                    recent = await self.memory.get_recent_messages(limit=20)
                    intent_result = await self.intent_detector.detect(recent)

                    await self.log(
                        "intent_detected",
                        json.dumps({"messages": new_messages}),
                        json.dumps({"intent": intent_result.intent, "reply": intent_result.reply, "item": intent_result.item}),
                    )

                    # Send reply via Supabase insert
                    if intent_result.reply:
                        reply_text = intent_result.reply.replace("\n", " ").strip()
                        await self._send_message(reply_text)
                        await self.memory.save_message("agent", reply_text, config.WHATSAPP_AGENT_USER)

                    # If food intent and no order already running, publish order event
                    if intent_result.intent == "order_food" and intent_result.item and not self._ordering:
                        self._ordering = True
                        await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})
                        logger.info(f"[WhatsAppAgent] Published ORDER_REQUESTED for: {intent_result.item}")

            except Exception as e:
                logger.error(f"[WhatsAppAgent] Error in polling loop: {e}")
                await self.log("error", str(e), status="error")

            await asyncio.sleep(config.POLL_INTERVAL)

    async def _check_for_new_messages(self) -> list[str]:
        """Query Supabase for new messages from the target contact since last check."""
        try:
            query = (
                self.supabase.table("chats")
                .select("content, created_at")
                .eq("conversation_id", self.conversation_id)
                .eq("sender_id", config.WHATSAPP_TARGET_ID)
                .order("created_at", desc=False)
                .limit(10)
            )

            # Only get messages newer than our last snapshot
            if self._last_seen_ts:
                query = query.gt("created_at", self._last_seen_ts)

            result = query.execute()

            if not result.data:
                return []

            # Update timestamp to the latest message we just fetched
            self._last_seen_ts = result.data[-1]["created_at"]

            new_messages = [row["content"] for row in result.data]
            return new_messages

        except Exception as e:
            logger.error(f"[WhatsAppAgent] Supabase query failed: {e}")
            return []

    async def _send_message(self, text: str):
        """Type and send message via the browser UI so the user can watch it happen."""
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
            logger.info(f"[WhatsAppAgent] Sent via UI: {text}")
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
