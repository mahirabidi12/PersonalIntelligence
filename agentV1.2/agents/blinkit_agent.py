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

logger = logging.getLogger(__name__)


class BlinkItAgent(BaseAgent):
    """
    V1.2 BlinkIt Agent — Improved with:
    - Automatic retry with backoff
    - Better error handling
    - Step-by-step logging
    - Works with our Blinkit2 clone
    """

    def __init__(self, browser: Browser, event_bus: EventBus, memory: Memory, intent_detector: IntentDetector):
        super().__init__("BlinkItAgent", browser, event_bus, memory)
        self.intent_detector = intent_detector
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)

    async def setup(self):
        self.set_status("running", "Setting up Blinkit")

    async def run(self, item: str = "", **kwargs):
        if not item:
            logger.error("[BlinkIt] No item specified")
            return

        self.set_status("running", f"Ordering: {item}")
        await self.log("order_start", f"Starting order for: {item}")

        for attempt in range(config.MAX_RETRIES + 1):
            try:
                await self._login()
                await self._search_item(item)
                options = await self._extract_options()

                if not options:
                    await self.log("no_products", f"No products found for: {item}", "warning")
                    if attempt < config.MAX_RETRIES:
                        await asyncio.sleep(2)
                        continue
                    await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": "No products found"})
                    return

                decision = await self.intent_detector.decide_food_option(options, item)
                chosen_idx = decision.get("chosen_index", 0)
                chosen_name = options[chosen_idx].get("name", item) if chosen_idx < len(options) else item
                await self.log("product_chosen", f"{chosen_name} (reason: {decision.get('reason', '')})")

                await self._add_to_cart_and_checkout(chosen_name)

                await self.event_bus.publish("ORDER_COMPLETED", {"item": item, "chosen": chosen_name})
                await self.log("order_complete", f"Successfully ordered: {chosen_name}")
                self.set_status("idle")
                return

            except Exception as e:
                logger.error(f"[BlinkIt] Attempt {attempt+1} failed: {e}")
                await self.log("order_retry", f"Attempt {attempt+1} failed: {e}", "error")
                if attempt < config.MAX_RETRIES:
                    await asyncio.sleep(3 * (attempt + 1))

        await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": "All retries exhausted"})
        self.set_status("error", "Order failed")

    async def _login(self):
        await self.log("step", "Navigating to Blinkit and logging in")
        login_agent = Agent(
            task=f"""
            Go to {config.BLINKIT_URL}
            If you see a Login page or Login button:
            1. Click Login
            2. Enter email: "{config.BLINKIT_EMAIL}"
            3. Enter password: "{config.BLINKIT_PASSWORD}"
            4. Click the login/submit button
            5. Wait for the home page to load
            If already logged in (products visible), skip login.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await login_agent.run()

    async def _search_item(self, item: str):
        await self.log("step", f"Searching for: {item}")
        search_agent = Agent(
            task=f"""
            Find the search bar/input on the page. Click it and type "{item}".
            Press Enter to search. Wait for results to appear.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await search_agent.run()
        await asyncio.sleep(4)

    async def _extract_options(self) -> list[dict]:
        await self.log("step", "Extracting product options")
        extract_agent = Agent(
            task="""
            Look at the product listings on the page.
            Extract each product's name and price as a JSON array.
            Example: [{"name": "Product A", "price": "₹120"}, {"name": "Product B", "price": "₹85"}]
            Return ONLY the JSON array. If no products, return [].
            """,
            llm=self.llm,
            browser=self.browser,
        )
        result = await extract_agent.run()
        result_text = result.final_result() if hasattr(result, 'final_result') else str(result)
        return self._parse_json_list(result_text)

    def _parse_json_list(self, text: str) -> list[dict]:
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

    async def _add_to_cart_and_checkout(self, product_name: str):
        await self.log("step", f"Adding to cart: {product_name}")
        cart_agent = Agent(
            task=f"""
            Find "{product_name}" in the product listings. Click "Add" or "ADD" button on it.
            Then click the cart button (usually top-right) to open cart.
            Click "Proceed to Checkout" or similar button.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await cart_agent.run()
        await asyncio.sleep(1)

        await self.log("step", "Completing checkout with COD")
        checkout_agent = Agent(
            task=f"""
            On the checkout page:
            1. Fill address if required (use "123 Test Street" / "Mumbai" / "Maharashtra" / "400001" / "9876543210")
            2. Select Cash on Delivery for payment
            3. Click "Place Order" to complete
            Wait for order confirmation.
            """,
            llm=self.llm,
            browser=self.browser,
        )
        await checkout_agent.run()
        await self.log("checkout_done", "Order placed for: " + product_name)
