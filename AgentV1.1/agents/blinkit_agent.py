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

logger = logging.getLogger(__name__)


class BlinkItAgent(BaseAgent):
    """
    BlinkeyIt ordering agent. Spawned on-demand when ORDER_REQUESTED fires.
    Opens BlinkeyIt in a new tab, searches for the item, picks the best option,
    adds to cart, and checks out via COD.
    """

    def __init__(self, browser_session: BrowserSession, event_bus: EventBus, memory: Memory, intent_detector: IntentDetector):
        super().__init__("BlinkItAgent", browser_session, event_bus, memory)
        self.intent_detector = intent_detector
        self.llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY)

    async def setup(self):
        """Navigate to BlinkeyIt and login if needed."""
        self.set_status("running", "Setting up BlinkeyIt")

    async def run(self, item: str = ""):
        """Full ordering flow: navigate → login → search → pick → cart → checkout."""
        if not item:
            logger.error("[BlinkItAgent] No item specified")
            return

        self.set_status("running", f"Ordering: {item}")
        logger.info(f"[BlinkItAgent] Starting order flow for: {item}")

        try:
            # Step 1: Navigate to BlinkeyIt and login
            await self._navigate_and_login()

            # Step 2: Search for the item
            await self._search_item(item)

            # Step 3: Extract available options
            options = await self._extract_options()

            if not options:
                logger.warning(f"[BlinkItAgent] No options found for: {item}")
                await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": "No products found"})
                return

            # Step 4: Pick the best option using LLM
            decision = await self.intent_detector.decide_food_option(options, item)
            chosen_index = decision.get("chosen_index", 0)
            chosen_name = options[chosen_index].get("name", item) if chosen_index < len(options) else item

            logger.info(f"[BlinkItAgent] Chose: {chosen_name} (index {chosen_index})")
            await self.log("decision", json.dumps(options), json.dumps(decision))

            # Step 5: Add to cart and checkout
            await self._add_to_cart_and_checkout(chosen_name)

            # Step 6: Publish success
            await self.event_bus.publish("ORDER_COMPLETED", {
                "item": item,
                "chosen": chosen_name,
                "status": "success",
            })
            self.set_status("idle", None)
            logger.info(f"[BlinkItAgent] Order completed for: {item}")

        except Exception as e:
            logger.error(f"[BlinkItAgent] Order failed for {item}: {e}")
            await self.log("order_failed", item, str(e), status="error")

            # Retry once
            try:
                logger.info(f"[BlinkItAgent] Retrying order for: {item}")
                await self._add_to_cart_and_checkout(item)
                await self.event_bus.publish("ORDER_COMPLETED", {"item": item, "status": "success_on_retry"})
            except Exception as retry_error:
                logger.error(f"[BlinkItAgent] Retry also failed: {retry_error}")
                await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": str(e)})
                self.set_status("error", str(e))

    async def _navigate_and_login(self):
        """Go to BlinkeyIt and login first — always login before anything else."""
        login_agent = Agent(
            task=f"""
            Go to {config.BLINKIT_URL}

            IMPORTANT: You MUST login first before doing anything else.
            1. Look for the "Login" button in the header and click it. It will take you to the login page.
            2. You will see two fields: "Email :" and "Password :".
            3. Enter email: "{config.BLINKIT_EMAIL}" in the "Enter your email" field.
            4. Enter password: "{config.BLINKIT_PASSWORD}" in the "Enter your password" field.
            5. Click the green "Login" submit button.
            6. Wait for the home page to fully load after login.

            If you are already logged in (you can see products or an "Account" dropdown), skip login.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await login_agent.run()
        await self.log("navigate_login", config.BLINKIT_URL)
        logger.info("[BlinkItAgent] Navigated to BlinkeyIt and logged in")

    async def _search_item(self, item: str):
        """Search for the requested item. Wait 5s after typing for results to load."""
        search_agent = Agent(
            task=f"""
            On the current page, find the search bar (it has placeholder text like "Search for kitkat and more.").
            Click on it and type "{item}".
            Then press Enter to search.
            IMPORTANT: After searching, WAIT and do nothing for a few seconds — the search results take time to load.
            Do NOT click anything until product cards are visible on the page.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await search_agent.run()

        # Explicit 5-second wait for search results to load
        logger.info(f"[BlinkItAgent] Waiting 5s for search results to load...")
        await asyncio.sleep(5)

        await self.log("search", item)
        logger.info(f"[BlinkItAgent] Searched for: {item}")

    async def _extract_options(self) -> list[dict]:
        """Extract product options from the search results page."""
        extract_agent = Agent(
            task="""
            Look at the product listings / search results on the page.
            Extract each product's name and price.
            Return ONLY a JSON array, nothing else.
            Example: [{"name": "Product A", "price": "₹120"}, {"name": "Product B", "price": "₹85"}]
            If no products are visible, return an empty array: []
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        result = await extract_agent.run()
        result_text = result.final_result() if hasattr(result, 'final_result') else str(result)

        # Parse options from result
        options = self._parse_options(result_text)
        logger.info(f"[BlinkItAgent] Found {len(options)} options")
        await self.log("extract_options", "", json.dumps(options))
        return options

    def _parse_options(self, text: str) -> list[dict]:
        """Parse JSON product list from browser-use output."""
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the text
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        logger.warning(f"[BlinkItAgent] Could not parse options from: {text[:200]}")
        return []

    async def _add_to_cart_and_checkout(self, product_name: str):
        """Click on the product, add to cart, and complete checkout."""
        # Step A: Click product and add to cart
        cart_agent = Agent(
            task=f"""
            Find the product named "{product_name}" (or the closest match) in the product listings.
            Click the green "Add" button on that product card to add it to cart.
            Do NOT click on the product itself — just click the "Add" button directly.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await cart_agent.run()
        await self.log("add_to_cart", product_name)
        logger.info(f"[BlinkItAgent] Added to cart: {product_name}")

        await asyncio.sleep(1)

        # Step B: Go to cart and checkout
        checkout_agent = Agent(
            task=f"""
            Now go to the shopping cart. Look for the green cart button in the top-right header (it shows item count and price, or says "My Cart").
            Click on it to open the cart.

            In the cart:
            1. Verify the item is there
            2. Click the green "Proceed" button at the bottom of the cart
            3. On the checkout page, you will see your address on the left and a summary on the right.
            4. DO NOT try to add a new address. Use whatever address is already shown.
            5. For payment: click the "Cash on Delivery" button (the one with green border). Do NOT click "Online Payment".
            6. Wait for the order confirmation.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await checkout_agent.run()
        await self.log("checkout", product_name)
        logger.info(f"[BlinkItAgent] Checkout completed for: {product_name}")

    async def teardown(self):
        """Cleanup."""
        self.set_status("idle", None)
        await super().teardown()
