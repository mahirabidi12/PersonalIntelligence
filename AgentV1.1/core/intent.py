import json
import logging

from openai import AsyncOpenAI

from config import config
from core.step_logger import log_step, StepType
from core.supermemory import SuperMemory
from models.schemas import ChatMessage, IntentResult
from prompts.girlfriend import build_system_prompt

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detects user intent from conversation history using LLM structured output.
    Incorporates SuperMemory for personality matching."""

    def __init__(self, supermemory: SuperMemory):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.supermemory = supermemory

        # Build the system prompt with supermemory + initial instruction
        self.system_prompt = build_system_prompt(
            supermemory_content=supermemory.get_personality_prompt(),
            initial_instruction=config.INITIAL_INSTRUCTION,
        )

    async def detect(self, messages: list[ChatMessage]) -> IntentResult:
        """Analyze conversation and return structured intent + reply matching user's style."""
        conversation_text = "\n".join(
            f"{msg.sender_name or msg.role}: {msg.content}" for msg in messages
        )

        last_msg = messages[-1].content if messages else ""
        await log_step("IntentDetector", StepType.REASON, f"Analyzing {len(messages)} messages for intent", f"last_message=\"{last_msg[:100]}\"")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"Here is the conversation so far:\n\n{conversation_text}\n\nRespond to the most recent message from {config.WHATSAPP_TARGET_CONTACT}. Stay in character.",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            raw = response.choices[0].message.content
            logger.info(f"Intent LLM raw response: {raw}")

            data = json.loads(raw)
            result = IntentResult(
                intent=data.get("intent", "normal_chat"),
                reply=data.get("reply"),
                item=data.get("item"),
                confidence=data.get("confidence", 0.5),
            )

            await log_step("IntentDetector", StepType.DECIDE, f"Classified intent as '{result.intent}'", f"confidence={result.confidence}, reply=\"{(result.reply or '')[:80]}\"")

            # Enforce price cap guardrail
            if result.intent == "order_food" and result.item:
                await log_step("IntentDetector", StepType.REASON, f"Food craving detected: '{result.item}'", f"price_cap=₹{self.supermemory.get_price_cap()}")
                logger.info(f"Food intent detected: {result.item} (price cap: ₹{self.supermemory.get_price_cap()})")

            logger.info(f"Detected intent: {result.intent} | item: {result.item} | confidence: {result.confidence}")
            return result

        except Exception as e:
            await log_step("IntentDetector", StepType.EVENT, "Intent detection failed, falling back to 'normal_chat'", f"error={str(e)}")
            logger.error(f"Intent detection failed: {e}")
            return IntentResult(
                intent="normal_chat",
                reply="hmm one sec",
                confidence=0.0,
            )

    async def generate_generic_reply(self, messages: list[dict], contact_name: str) -> str:
        """Generate a one-shot casual reply for a non-GF contact."""
        from prompts.generic import build_generic_prompt

        await log_step("IntentDetector", StepType.REASON, f"Generating casual reply for contact '{contact_name}'", f"context_messages={len(messages)}")

        prompt = build_generic_prompt(
            supermemory_content=self.supermemory.get_personality_prompt(),
            contact_name=contact_name,
        )

        conversation_text = "\n".join(
            f"{msg.get('sender_name', msg.get('sender_id', 'Unknown'))}: {msg.get('content', '')}"
            for msg in messages
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"Here is the recent conversation:\n\n{conversation_text}\n\nReply to the most recent message from {contact_name}. Stay in character as Saswata.",
                    },
                ],
                temperature=0.7,
            )

            reply = response.choices[0].message.content.strip().strip('"').strip("'")
            await log_step("IntentDetector", StepType.DECIDE, f"Generated generic reply for '{contact_name}'", f"reply=\"{reply[:80]}\"")
            logger.info(f"Generic reply for {contact_name}: {reply}")
            return reply

        except Exception as e:
            await log_step("IntentDetector", StepType.EVENT, f"Generic reply generation failed for '{contact_name}'", f"error={str(e)}")
            logger.error(f"Generic reply generation failed for {contact_name}: {e}")
            return "haan bro, baad mein baat karta hoon"

    async def decide_food_option(self, options: list[dict], requested_item: str) -> dict:
        """Pick the best food option from a list using LLM. Respects price cap."""
        from prompts.decision import DECISION_SYSTEM_PROMPT

        price_cap = self.supermemory.get_price_cap()

        options_text = "\n".join(
            f"{i}. {opt.get('name', 'Unknown')} - {opt.get('price', 'N/A')}"
            for i, opt in enumerate(options)
        )

        await log_step("IntentDetector", StepType.REASON, f"Evaluating {len(options)} food options for '{requested_item}'", f"budget=₹{price_cap}")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"User requested: {requested_item}\nMax budget: ₹{price_cap}\n\nAvailable options:\n{options_text}\n\nPick the best option within budget.",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            raw = response.choices[0].message.content
            logger.info(f"Decision LLM raw response: {raw}")
            decision = json.loads(raw)
            chosen_idx = decision.get("chosen_index", 0)
            chosen_name = options[chosen_idx].get("name", "Unknown") if chosen_idx < len(options) else "Unknown"
            await log_step("IntentDetector", StepType.DECIDE, f"Picked '{chosen_name}' (index {chosen_idx})", f"reason={decision.get('reason', 'N/A')}")
            return decision

        except Exception as e:
            await log_step("IntentDetector", StepType.EVENT, "Food decision failed, defaulting to first option", f"error={str(e)}")
            logger.error(f"Food decision failed: {e}")
            return {"chosen_index": 0, "reason": "Defaulting to first option"}
