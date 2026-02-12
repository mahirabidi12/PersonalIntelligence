import asyncio
import logging

from browser_use import Agent, Browser
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from config import config
from core.memory import Memory
from events.bus import EventBus

logger = logging.getLogger(__name__)


class BrowserTaskAgent(BaseAgent):
    """
    V1.2 NEW — General-purpose browser task agent.
    Can execute arbitrary browsing tasks: navigate, extract, interact.
    """

    def __init__(self, browser: Browser, event_bus: EventBus, memory: Memory):
        super().__init__("BrowserTaskAgent", browser, event_bus, memory)
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)

    async def setup(self):
        self.set_status("idle")

    async def run(self, task_id: str = "", description: str = "", url: str = "", **kwargs):
        self.set_status("running", description[:80])
        await self.log("task_start", f"[{task_id}] {description}")

        try:
            full_task = description
            if url:
                full_task = f"First, navigate to {url}. Then: {description}"

            agent = Agent(
                task=full_task,
                llm=self.llm,
                browser=self.browser,
            )
            result = await agent.run()
            result_text = result.final_result() if hasattr(result, 'final_result') else str(result)

            await self.log("task_complete", f"[{task_id}] Result: {result_text[:200]}")
            await self.memory.update_task(task_id, "completed", result=result_text)
            await self.event_bus.publish("TASK_COMPLETED", {
                "task_id": task_id, "result": result_text
            })

            self.set_status("idle")
            return result_text

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[BrowserTask] Failed: {error_msg}")
            await self.log("task_failed", f"[{task_id}] {error_msg}", "error")
            await self.memory.update_task(task_id, "failed", error=error_msg)
            await self.event_bus.publish("TASK_FAILED", {
                "task_id": task_id, "error": error_msg
            })
            self.set_status("error", error_msg)
            return None
