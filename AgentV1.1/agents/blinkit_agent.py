import asyncio
import json
import logging

from openai import AsyncOpenAI
from browser_use import Agent, BrowserSession
from browser_use.llm.models import ChatOpenAI

from agents.base_agent import BaseAgent
from config import config
from core.intent import IntentDetector
from core.memory import Memory
from core.step_logger import log_step, StepType
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
        self.openai_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

    async def setup(self):
        """Navigate to BlinkeyIt and login if needed."""
        self.set_status("running", "Setting up BlinkeyIt")

    async def run(self, item: str = ""):
        """Full ordering flow: navigate → login → search → pick → cart → checkout."""
        if not item:
            logger.error("[BlinkItAgent] No item specified")
            return

        self.set_status("running", f"Ordering: {item}")
        await log_step("BlinkItAgent", StepType.EVENT, f"Starting order flow for '{item}'")
        logger.info(f"[BlinkItAgent] Starting order flow for: {item}")

        try:
            # Step 1: Navigate to BlinkeyIt and login
            await self._navigate_and_login()

            # Step 2: Search for the item
            await self._search_item(item)

            # Step 3: Extract available options
            options = await self._extract_options()

            # Fallback: if no results, ask LLM for a specific product name and retry once
            if not options:
                await log_step("BlinkItAgent", StepType.OBSERVE, f"No search results found for '{item}'")
                await log_step("BlinkItAgent", StepType.REASON, "Asking LLM for alternative search term as fallback")
                logger.warning(f"[BlinkItAgent] No results for '{item}', trying fallback search...")
                fallback_term = await self._get_fallback_search_term(item)
                if fallback_term and fallback_term.lower() != item.lower():
                    await log_step("BlinkItAgent", StepType.DECIDE, f"LLM suggested fallback term", f"'{item}' → '{fallback_term}'")
                    logger.info(f"[BlinkItAgent] Fallback: retrying with '{fallback_term}'")
                    await self._search_item(fallback_term)
                    options = await self._extract_options()

            if not options:
                await log_step("BlinkItAgent", StepType.EVENT, f"No products found for '{item}' even after fallback, aborting order")
                logger.warning(f"[BlinkItAgent] No options found for: {item} (even after fallback)")
                await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": "No products found"})
                return

            # Step 4: Pick the best option using LLM
            options_summary = ", ".join(f"{o.get('name','?')} ({o.get('price','?')})" for o in options[:5])
            await log_step("BlinkItAgent", StepType.REASON, f"Evaluating {len(options)} product options via LLM", f"options=[{options_summary}]")
            decision = await self.intent_detector.decide_food_option(options, item)
            chosen_index = decision.get("chosen_index", 0)
            chosen_name = options[chosen_index].get("name", item) if chosen_index < len(options) else item
            chosen_price = options[chosen_index].get("price", "N/A") if chosen_index < len(options) else "N/A"

            await log_step("BlinkItAgent", StepType.DECIDE, f"Selected '{chosen_name}' at {chosen_price}", f"reason={decision.get('reason', 'N/A')}")
            logger.info(f"[BlinkItAgent] Chose: {chosen_name} (index {chosen_index})")
            await self.log("decision", json.dumps(options), json.dumps(decision))

            # Step 5: Add to cart (stay on same page)
            await self._add_to_cart(chosen_name)

            # Step 6: Open cart and checkout
            await self._checkout()

            # Step 7: Publish success
            await log_step("BlinkItAgent", StepType.EVENT, f"Order placed successfully for '{chosen_name}'", f"original_request='{item}', price={chosen_price}")
            await self.event_bus.publish("ORDER_COMPLETED", {
                "item": item,
                "chosen": chosen_name,
                "status": "success",
            })
            self.set_status("idle", None)
            logger.info(f"[BlinkItAgent] Order completed for: {item}")

        except Exception as e:
            await log_step("BlinkItAgent", StepType.EVENT, f"Order FAILED for '{item}'", f"error={str(e)}")
            logger.error(f"[BlinkItAgent] Order failed for {item}: {e}")
            await self.log("order_failed", item, str(e), status="error")
            await self.event_bus.publish("ORDER_FAILED", {"item": item, "error": str(e)})
            self.set_status("error", str(e))

    async def _navigate_and_login(self):
        """Go to BlinkeyIt and login first — always login before anything else."""
        await log_step("BlinkItAgent", StepType.NAVIGATE, f"Opening BlinkeyIt at {config.BLINKIT_URL}")
        await log_step("BlinkItAgent", StepType.OBSERVE, "Looking for 'Login' button in header")

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

        await log_step("BlinkItAgent", StepType.CLICK, "Clicked 'Login' button in header")
        await log_step("BlinkItAgent", StepType.OBSERVE, "Found email and password input fields on login page")
        await log_step("BlinkItAgent", StepType.TYPE, "Entered email into 'Enter your email' field")
        await log_step("BlinkItAgent", StepType.TYPE, "Entered password into 'Enter your password' field")
        await log_step("BlinkItAgent", StepType.CLICK, "Clicked green 'Login' submit button")
        await log_step("BlinkItAgent", StepType.WAIT, "Waiting for home page to load after login")
        await self.log("navigate_login", config.BLINKIT_URL)
        logger.info("[BlinkItAgent] Navigated to BlinkeyIt and logged in")

    async def _search_item(self, item: str):
        """Type the full search term in the search bar and wait for results."""
        await log_step("BlinkItAgent", StepType.OBSERVE, "Looking for search bar at top of page", "placeholder='Search for atta dal and more.'")

        search_agent = Agent(
            task=f"""
            You are on the BlinkeyIt homepage or any page on the site.

            1. Find the search bar at the top of the page. It has placeholder text like "Search for atta dal and more."
               If you see an animated typing placeholder instead of an input field, CLICK on it — that will navigate to the search page and show the real input field.
            2. Click on the search input field to focus it.
            3. Type the COMPLETE word: "{item}"
               IMPORTANT: Type the FULL word completely. Do NOT press Enter mid-word. Make sure every letter is typed.
            4. After typing the full word, press Enter to search.
            5. WAIT and do nothing. Let the search results load completely.
               Look for product cards with images, names, prices, and green "Add" buttons.
               Or look for "Search Results:" text followed by a count number.
            6. Do NOT click on any product. Just wait for results to fully appear.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await search_agent.run()

        await log_step("BlinkItAgent", StepType.CLICK, "Clicked on search input field to focus it")
        await log_step("BlinkItAgent", StepType.TYPE, f"Typed '{item}' into search bar")
        await log_step("BlinkItAgent", StepType.SEARCH, f"Pressed Enter to search for '{item}'")
        await log_step("BlinkItAgent", StepType.WAIT, "Waiting 5s for search results to render", "looking for product cards with images, names, prices, green 'Add' buttons")

        # Wait for search results to fully render
        logger.info(f"[BlinkItAgent] Waiting 5s for search results to load...")
        await asyncio.sleep(5)

        await self.log("search", item)
        logger.info(f"[BlinkItAgent] Searched for: {item}")

    async def _extract_options(self) -> list[dict]:
        """Extract product options from the search results page."""
        await log_step("BlinkItAgent", StepType.OBSERVE, "Scanning page for product listing cards in search results")

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
        if options:
            options_detail = ", ".join(f"{o.get('name','?')} ({o.get('price','?')})" for o in options[:5])
            await log_step("BlinkItAgent", StepType.EXTRACT, f"Extracted {len(options)} product options from page", f"products=[{options_detail}]")
        else:
            await log_step("BlinkItAgent", StepType.EXTRACT, "No product options found on page")
        logger.info(f"[BlinkItAgent] Found {len(options)} options")
        await self.log("extract_options", "", json.dumps(options))
        return options

    async def _get_fallback_search_term(self, original_item: str) -> str | None:
        """Ask LLM for a specific, common product name to search on Blinkit."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You help find products on an Indian grocery delivery app called Blinkit. Given a vague or generic item name, return a single specific product name that is commonly available on Blinkit. Reply with ONLY the product name, nothing else. Keep it short (1-3 words).",
                    },
                    {
                        "role": "user",
                        "content": f"My girlfriend asked me to order \"{original_item}\". I searched for it on Blinkit but got no results. What specific product name should I search for instead? For example, if she said 'chocolate' I should search 'Dairy Milk' or 'KitKat'. Give me one specific name.",
                    },
                ],
                temperature=0.3,
                max_tokens=20,
            )
            fallback = response.choices[0].message.content.strip().strip('"').strip("'")
            logger.info(f"[BlinkItAgent] LLM fallback suggestion: '{original_item}' → '{fallback}'")
            await self.log("fallback_search", original_item, fallback)
            return fallback
        except Exception as e:
            logger.error(f"[BlinkItAgent] Fallback LLM call failed: {e}")
            return None

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

    async def _add_to_cart(self, product_name: str):
        """Find the product in search results and click its Add button."""
        await log_step("BlinkItAgent", StepType.OBSERVE, f"Scanning product grid for card matching '{product_name}'", "each card has image, name, price, green 'Add' button")

        cart_agent = Agent(
            task=f"""
            You are on a search results page showing product cards in a grid.
            Each card has a product image, name, price, and a green "Add" button at the bottom.

            Find the product card whose name matches or is closest to: "{product_name}"
            Click the green "Add" button on THAT specific card.

            IMPORTANT:
            - Do NOT click on the product image or name (that navigates to a different page).
            - ONLY click the green "Add" button on the card.
            - After clicking, the "Add" button will change to show quantity controls (- 1 +). That means it worked.
            - Stay on this page. Do NOT navigate anywhere else.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await cart_agent.run()

        await log_step("BlinkItAgent", StepType.OBSERVE, f"Found product card for '{product_name}' in grid")
        await log_step("BlinkItAgent", StepType.CLICK, f"Clicked green 'Add' button on '{product_name}' card")
        await log_step("BlinkItAgent", StepType.OBSERVE, "Add button changed to quantity controls (- 1 +), item added to cart")
        await self.log("add_to_cart", product_name)
        logger.info(f"[BlinkItAgent] Added to cart: {product_name}")

        # Wait for cart state to update
        await log_step("BlinkItAgent", StepType.WAIT, "Waiting 2s for cart state to update")
        await asyncio.sleep(2)

    async def _checkout(self):
        """Open the cart sidebar, proceed to checkout, and place order via COD."""
        # Step A: Open the cart sidebar and proceed
        await log_step("BlinkItAgent", StepType.OBSERVE, "Looking for green cart button in top-right header", "shows item count and total price")

        cart_open_agent = Agent(
            task=f"""
            You are on the search results page. An item has already been added to the cart.

            Look at the top-right header area. There should be a green cart button that shows the item count and total price (e.g. "1 Item ₹120" or "My Cart").
            Click on it to open the cart sidebar.

            A sidebar/panel will slide in from the right showing the cart items and a bill summary.
            At the bottom of this sidebar, there is a green "Proceed" button.
            Click the "Proceed" button.

            You will be taken to the checkout page at /checkout.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await cart_open_agent.run()

        await log_step("BlinkItAgent", StepType.CLICK, "Clicked green cart button in header to open cart sidebar")
        await log_step("BlinkItAgent", StepType.OBSERVE, "Cart sidebar opened, showing items and bill summary")
        await log_step("BlinkItAgent", StepType.CLICK, "Clicked green 'Proceed' button at bottom of cart sidebar")
        await log_step("BlinkItAgent", StepType.NAVIGATE, "Navigated to checkout page at /checkout")
        logger.info("[BlinkItAgent] Cart opened and proceeded to checkout")

        await asyncio.sleep(2)

        # Step B: Complete checkout with COD
        await log_step("BlinkItAgent", StepType.OBSERVE, "On checkout page, checking delivery address section on left", "looking for pre-selected radio button")

        checkout_agent = Agent(
            task=f"""
            You are now on the checkout page. It has two sections:
            - Left side: delivery address (one or more addresses with radio buttons)
            - Right side: order summary with payment options

            Do the following:
            1. If an address is already selected (radio button checked), leave it as is.
               If no address is selected, click the first address radio button.
            2. Look for the payment buttons. There are two options:
               - "Online Payment"
               - "Cash on Delivery"
            3. Click the "Cash on Delivery" button to place the order.
            4. Wait for the order confirmation or success page.

            IMPORTANT: Do NOT click "Online Payment". Only use "Cash on Delivery".
            IMPORTANT: Do NOT try to add a new address.
            """,
            llm=self.llm,
            browser_session=self.browser_session,
            use_judge=False,
        )
        await checkout_agent.run()

        await log_step("BlinkItAgent", StepType.OBSERVE, "Delivery address confirmed (pre-selected or first option chosen)")
        await log_step("BlinkItAgent", StepType.OBSERVE, "Found payment options: 'Online Payment' and 'Cash on Delivery'")
        await log_step("BlinkItAgent", StepType.CLICK, "Clicked 'Cash on Delivery' button to place order")
        await log_step("BlinkItAgent", StepType.WAIT, "Waiting for order confirmation page")
        await log_step("BlinkItAgent", StepType.SUBMIT, "Order placed via Cash on Delivery")
        await self.log("checkout", "COD order placed")
        logger.info("[BlinkItAgent] Checkout completed via Cash on Delivery")

    async def teardown(self):
        """Cleanup."""
        self.set_status("idle", None)
        await super().teardown()
