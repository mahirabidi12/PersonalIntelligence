import json
import logging

from openai import AsyncOpenAI

from config import config
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

            # Enforce price cap guardrail
            if result.intent == "order_food" and result.item:
                logger.info(f"Food intent detected: {result.item} (price cap: ₹{self.supermemory.get_price_cap()})")

            logger.info(f"Detected intent: {result.intent} | item: {result.item} | confidence: {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return IntentResult(
                intent="normal_chat",
                reply="hmm one sec",
                confidence=0.0,
            )

    async def decide_food_option(self, options: list[dict], requested_item: str) -> dict:
        """Pick the best food option from a list using LLM. Respects price cap."""
        from prompts.decision import DECISION_SYSTEM_PROMPT

        price_cap = self.supermemory.get_price_cap()

        options_text = "\n".join(
            f"{i}. {opt.get('name', 'Unknown')} - {opt.get('price', 'N/A')}"
            for i, opt in enumerate(options)
        )

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
            return json.loads(raw)

        except Exception as e:
            logger.error(f"Food decision failed: {e}")
            return {"chosen_index": 0, "reason": "Defaulting to first option"}
