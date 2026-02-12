import json
import logging

from openai import AsyncOpenAI

from config import config
from core.supermemory import SuperMemory
from models.schemas import ChatMessage, IntentResult
from prompts.girlfriend import build_system_prompt

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detects intent from conversation using LLM. Incorporates SuperMemory for personality."""

    def __init__(self, supermemory: SuperMemory):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.LLM_MODEL
        self.supermemory = supermemory
        self.system_prompt = build_system_prompt(
            supermemory_content=supermemory.get_personality_prompt(),
            initial_instruction=config.INITIAL_INSTRUCTION,
        )

    async def detect(self, messages: list[ChatMessage]) -> IntentResult:
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
                        "content": f"Conversation:\n\n{conversation_text}\n\nRespond to the most recent message from {config.WHATSAPP_TARGET_CONTACT}. Stay in character.",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            raw = response.choices[0].message.content
            logger.info(f"Intent LLM: {raw[:200]}")
            data = json.loads(raw)
            return IntentResult(
                intent=data.get("intent", "normal_chat"),
                reply=data.get("reply"),
                item=data.get("item"),
                confidence=data.get("confidence", 0.5),
            )
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            return IntentResult(intent="normal_chat", reply="hmm one sec", confidence=0.0)

    async def decide_food_option(self, options: list[dict], requested_item: str) -> dict:
        from prompts.decision import DECISION_SYSTEM_PROMPT
        price_cap = self.supermemory.get_price_cap()
        options_text = "\n".join(
            f"{i}. {opt.get('name', 'Unknown')} - {opt.get('price', 'N/A')}" for i, opt in enumerate(options)
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Requested: {requested_item}\nBudget: ₹{price_cap}\n\nOptions:\n{options_text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Food decision failed: {e}")
            return {"chosen_index": 0, "reason": "Default first option"}

    async def general_task_analysis(self, task_description: str, page_content: str) -> dict:
        """Analyze a general browsing task and decide next action."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a browser automation agent. Given a task and current page content,
                        decide the next action. Respond with JSON:
                        {"action": "click|type|scroll|navigate|extract|done", "target": "element description", "value": "text to type if action is type", "reasoning": "why this action"}"""
                    },
                    {"role": "user", "content": f"Task: {task_description}\n\nPage content:\n{page_content[:3000]}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Task analysis failed: {e}")
            return {"action": "done", "reasoning": str(e)}
