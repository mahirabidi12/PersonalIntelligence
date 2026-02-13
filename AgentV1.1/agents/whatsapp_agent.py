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
from core.step_logger import log_step, StepType
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

        # Idle-time one-shot replies to other contacts (only if instruction says so)
        self._idle_seconds: int = 0
        self._handled_contacts: set[str] = set()
        self._reply_other_chats: bool = self._should_reply_other_chats()

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
        msg = f"done meri jaan, {item} aa raha hai tere liye"
        self._pending_notifications.append(msg)
        await log_step("WhatsAppAgent", StepType.EVENT, f"Order completed for '{item}', queued confirmation message")
        logger.info(f"[WhatsAppAgent] Queued order completion notification for: {item}")

    async def _on_order_failed(self, payload: dict):
        """Queue a failure message to send in WhatsApp."""
        self._ordering = False
        item = payload.get("item", "that")
        error = payload.get("error", "something went wrong")
        self._pending_notifications.append(
            f"ummm {item} nahi mil raha abhi, baad mein try karta hoon"
        )
        await log_step("WhatsAppAgent", StepType.EVENT, f"Order failed for '{item}', queued failure notification", f"error={error}")
        logger.info(f"[WhatsAppAgent] Queued order failure notification for: {item}")

    async def setup(self):
        """Navigate to WhatsApp, login as agent user, open target contact chat."""
        self.set_status("running", "Setting up WhatsApp")

        await log_step("WhatsAppAgent", StepType.NAVIGATE, f"Opening WhatsApp at {config.WHATSAPP_URL}")
        await log_step("WhatsAppAgent", StepType.OBSERVE, "Looking for 'Pick a User' screen with radio buttons")

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

        await log_step("WhatsAppAgent", StepType.CLICK, f"Selected user '{config.WHATSAPP_AGENT_USER}' from radio buttons")
        await log_step("WhatsAppAgent", StepType.CLICK, "Clicked 'Enter Chat' button to login")
        await log_step("WhatsAppAgent", StepType.OBSERVE, f"Scanning contacts list on left sidebar for '{config.WHATSAPP_TARGET_CONTACT}'")
        await log_step("WhatsAppAgent", StepType.CLICK, f"Clicked on contact '{config.WHATSAPP_TARGET_CONTACT}' to open chat")
        await self.log("setup", f"Navigated to WhatsApp and opened chat with {config.WHATSAPP_TARGET_CONTACT}")

        # Load last 5 messages into memory for context, and reply if latest is from Ananya
        await self._bootstrap_conversation()

        logger.info(f"[WhatsAppAgent] Setup complete. Chatting as {config.WHATSAPP_AGENT_USER} with {config.WHATSAPP_TARGET_CONTACT}")
        logger.info(f"[WhatsAppAgent] Conversation ID: {self.conversation_id}")
        logger.info(f"[WhatsAppAgent] Using Supabase for message read/write (no browser scraping)")

    async def _bootstrap_conversation(self):
        """Load last 5 messages into memory. If the latest is from the target, reply immediately."""
        await log_step("WhatsAppAgent", StepType.EXTRACT, "Fetching last 5 messages from Supabase for conversation context")

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
            await log_step("WhatsAppAgent", StepType.OBSERVE, "No existing messages found in conversation")
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
        await log_step("WhatsAppAgent", StepType.EXTRACT, f"Loaded {len(messages)} messages into memory for context")
        logger.info(f"[WhatsAppAgent] Loaded {len(messages)} messages into memory")
        logger.info(f"[WhatsAppAgent] Last message timestamp: {self._last_seen_ts}")

        # If the latest message is from the target contact, reply now
        latest = messages[-1]
        if latest["sender_id"] == config.WHATSAPP_TARGET_ID:
            await log_step("WhatsAppAgent", StepType.RECEIVE, f"Latest message is from {config.WHATSAPP_TARGET_CONTACT}", f"content=\"{latest['content']}\"")
            logger.info(f"[WhatsAppAgent] Latest message is from {config.WHATSAPP_TARGET_CONTACT}: \"{latest['content']}\" — replying immediately")

            recent = await self.memory.get_recent_messages(limit=20)
            await log_step("WhatsAppAgent", StepType.REASON, "Sending conversation to LLM for intent detection")
            intent_result = await self.intent_detector.detect(recent)

            await log_step("WhatsAppAgent", StepType.DECIDE, f"Intent classified as '{intent_result.intent}'", f"confidence={intent_result.confidence}, item={intent_result.item}")

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
                await log_step("WhatsAppAgent", StepType.EVENT, f"Food craving detected, triggering order for '{intent_result.item}'")
                await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})
                logger.info(f"[WhatsAppAgent] Published ORDER_REQUESTED for: {intent_result.item}")
        else:
            await log_step("WhatsAppAgent", StepType.OBSERVE, f"Latest message is from us, waiting for {config.WHATSAPP_TARGET_CONTACT} to reply")
            logger.info(f"[WhatsAppAgent] Latest message is from us — waiting for {config.WHATSAPP_TARGET_CONTACT}")

    async def run(self):
        """Main polling loop: check Supabase for new messages, detect intent, reply."""
        self._running = True
        self.set_status("running", "Polling for messages via Supabase")
        await log_step("WhatsAppAgent", StepType.EVENT, f"Starting message polling loop", f"interval={config.POLL_INTERVAL}s")

        while self._running:
            try:
                # Send any pending notifications first
                await self._send_pending_notifications()

                # Check Supabase for new messages from target contact
                new_messages = await self._check_for_new_messages()

                if new_messages:
                    self._idle_seconds = 0  # GF messaged, reset idle timer
                    for msg_text in new_messages:
                        await log_step("WhatsAppAgent", StepType.RECEIVE, f"New message from {config.WHATSAPP_TARGET_CONTACT}", f"content=\"{msg_text}\"")
                    logger.info(f"[WhatsAppAgent] Found {len(new_messages)} new message(s) from {config.WHATSAPP_TARGET_CONTACT}")

                    # Save new messages to memory
                    for msg_text in new_messages:
                        await self.memory.save_message("user", msg_text, config.WHATSAPP_TARGET_CONTACT)

                    # Get full conversation context and detect intent
                    recent = await self.memory.get_recent_messages(limit=20)
                    await log_step("WhatsAppAgent", StepType.REASON, "Analyzing conversation for intent detection", f"context_messages={len(recent)}")
                    intent_result = await self.intent_detector.detect(recent)

                    await log_step("WhatsAppAgent", StepType.DECIDE, f"Intent: '{intent_result.intent}'", f"confidence={intent_result.confidence}, item={intent_result.item}, reply_length={len(intent_result.reply or '')}")

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
                        await log_step("WhatsAppAgent", StepType.EVENT, f"Food craving detected, publishing ORDER_REQUESTED", f"item='{intent_result.item}'")
                        await self.event_bus.publish("ORDER_REQUESTED", {"item": intent_result.item})
                        logger.info(f"[WhatsAppAgent] Published ORDER_REQUESTED for: {intent_result.item}")
                else:
                    # GF is quiet — track idle time and reply to other contacts if enabled
                    if self._reply_other_chats:
                        self._idle_seconds += config.POLL_INTERVAL

                        # After 30s idle, reply to one other contact (one-shot)
                        if self._idle_seconds >= 30:
                            await log_step("WhatsAppAgent", StepType.REASON, f"Idle for {self._idle_seconds}s, switching to reply to another contact")
                            await self._reply_to_next_contact()
                            self._idle_seconds = 0

            except Exception as e:
                await log_step("WhatsAppAgent", StepType.EVENT, f"Error in polling loop", f"error={str(e)}")
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
            await log_step("WhatsAppAgent", StepType.OBSERVE, "Looking for message input field at bottom of chat area")
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
            await log_step("WhatsAppAgent", StepType.CLICK, "Clicked on message input field to focus it")
            await log_step("WhatsAppAgent", StepType.TYPE, f"Typed message into input field", f"text=\"{text}\"")
            await log_step("WhatsAppAgent", StepType.SUBMIT, "Pressed Enter to send the message")
            await log_step("WhatsAppAgent", StepType.SEND, f"Message sent to {config.WHATSAPP_TARGET_CONTACT}", f"content=\"{text}\"")
            logger.info(f"[WhatsAppAgent] Sent via UI: {text}")
            await self.log("send_message", text)
        except Exception as e:
            await log_step("WhatsAppAgent", StepType.EVENT, f"Failed to send message via browser UI", f"error={str(e)}")
            logger.error(f"[WhatsAppAgent] Failed to send message: {e}")

    async def _send_pending_notifications(self):
        """Send any queued notification messages."""
        while self._pending_notifications:
            msg = self._pending_notifications.pop(0)
            await self._send_message(msg)
            await self.memory.save_message("agent", msg, config.WHATSAPP_AGENT_USER)

    @staticmethod
    def _should_reply_other_chats() -> bool:
        """Check if INITIAL_INSTRUCTION mentions replying to other chats."""
        instruction = config.INITIAL_INSTRUCTION.lower()
        keywords = ["other chat", "all chat", "other contact", "all contact",
                     "keep chats updated", "reply to others", "reply others",
                     "other conversations", "all conversations"]
        match = any(kw in instruction for kw in keywords)
        if match:
            logger.info("[WhatsAppAgent] Instruction includes other-chats — multi-contact replies ENABLED")
        else:
            logger.info("[WhatsAppAgent] Instruction is GF-only — multi-contact replies DISABLED")
        return match

    def _get_conversation_id(self, contact_id: str) -> str:
        """Generate conversation_id for a contact (same logic as frontend)."""
        ids = sorted([config.WHATSAPP_USER_ID, contact_id])
        return f"{ids[0]}-{ids[1]}-chat"

    async def _reply_to_next_contact(self):
        """Pick the next un-handled contact, read last 5 msgs via API, then
        navigate to their chat in the browser, type & send the reply, and
        navigate back to Ananya's chat."""
        for contact_id, contact_name in config.CONTACTS.items():
            if contact_id in self._handled_contacts:
                continue

            conv_id = self._get_conversation_id(contact_id)

            await log_step("WhatsAppAgent", StepType.NAVIGATE, f"Switching to contact '{contact_name}' for idle-time reply")

            # Step 1: Navigate to this contact's chat first
            await self._navigate_to_contact(contact_name)

            # Step 2: Read last 5 messages from Supabase API
            await log_step("WhatsAppAgent", StepType.EXTRACT, f"Fetching last 5 messages for '{contact_name}' from Supabase")
            try:
                result = (
                    self.supabase.table("chats")
                    .select("sender_id, content, created_at")
                    .eq("conversation_id", conv_id)
                    .order("created_at", desc=True)
                    .limit(5)
                    .execute()
                )
            except Exception as e:
                await log_step("WhatsAppAgent", StepType.EVENT, f"Failed to fetch messages for '{contact_name}'", f"error={str(e)}")
                logger.error(f"[WhatsAppAgent] Failed to fetch messages for {contact_name}: {e}")
                self._handled_contacts.add(contact_id)
                await self._navigate_to_contact(config.WHATSAPP_TARGET_CONTACT)
                continue

            if not result.data:
                await log_step("WhatsAppAgent", StepType.OBSERVE, f"No messages found with '{contact_name}', skipping")
                self._handled_contacts.add(contact_id)
                logger.info(f"[WhatsAppAgent] No messages with {contact_name}, skipping")
                await self._navigate_to_contact(config.WHATSAPP_TARGET_CONTACT)
                continue

            messages = list(reversed(result.data))

            # If last message is from us, no reply needed
            if messages[-1]["sender_id"] == config.WHATSAPP_USER_ID:
                await log_step("WhatsAppAgent", StepType.OBSERVE, f"Last message to '{contact_name}' is from us, no reply needed")
                self._handled_contacts.add(contact_id)
                logger.info(f"[WhatsAppAgent] Last msg to {contact_name} is from us, skipping")
                await self._navigate_to_contact(config.WHATSAPP_TARGET_CONTACT)
                continue

            # Add sender names for LLM context
            for msg in messages:
                if msg["sender_id"] == config.WHATSAPP_USER_ID:
                    msg["sender_name"] = config.WHATSAPP_AGENT_USER
                else:
                    msg["sender_name"] = contact_name

            # Step 3: Generate reply text via LLM
            await log_step("WhatsAppAgent", StepType.REASON, f"Generating casual reply for '{contact_name}' via LLM", f"context_messages={len(messages)}")
            reply = await self.intent_detector.generate_generic_reply(messages, contact_name)
            reply = reply.replace("\n", " ").strip()
            await log_step("WhatsAppAgent", StepType.DECIDE, f"Generated reply for '{contact_name}'", f"reply=\"{reply}\"")

            # Step 4: Type and send via browser UI
            await self._send_message(reply)

            # Step 5: Navigate back to Ananya's chat
            await log_step("WhatsAppAgent", StepType.NAVIGATE, f"Navigating back to {config.WHATSAPP_TARGET_CONTACT}'s chat")
            await self._navigate_to_contact(config.WHATSAPP_TARGET_CONTACT)

            self._handled_contacts.add(contact_id)
            await self.log("one_shot_reply", contact_name, reply)
            logger.info(f"[WhatsAppAgent] One-shot reply to {contact_name}: {reply}")
            return  # Only one contact per idle cycle

        # If we get here, all contacts are handled
        logger.debug("[WhatsAppAgent] All contacts replied to, back to Ananya-only mode")

    async def _navigate_to_contact(self, contact_name: str):
        """Click on a contact in the sidebar to open their chat."""
        try:
            await log_step("WhatsAppAgent", StepType.OBSERVE, f"Scanning contacts sidebar for '{contact_name}'")
            nav_agent = Agent(
                task=f"""
                Look at the contacts list on the left side of the page.
                Find the contact named "{contact_name}" and click on it to open their chat.
                Wait for the chat to load.
                """,
                llm=self.llm,
                browser_session=self.browser_session,
                use_judge=False,
            )
            await nav_agent.run()
            await log_step("WhatsAppAgent", StepType.CLICK, f"Clicked on '{contact_name}' in contacts sidebar")
            await log_step("WhatsAppAgent", StepType.WAIT, f"Waiting for {contact_name}'s chat to load")
            logger.info(f"[WhatsAppAgent] Navigated to {contact_name}'s chat")
            await asyncio.sleep(1)
        except Exception as e:
            await log_step("WhatsAppAgent", StepType.EVENT, f"Failed to navigate to '{contact_name}'", f"error={str(e)}")
            logger.error(f"[WhatsAppAgent] Failed to navigate to {contact_name}: {e}")

    async def teardown(self):
        """Stop the polling loop."""
        self._running = False
        await super().teardown()
