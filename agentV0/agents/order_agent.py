"""
Order Agent — Uses browser-use to operate the BlinkIt clone.

Flow:
1. Opens browser → navigates to BlinkIt clone
2. Logs in with credentials
3. Searches for the requested item
4. Adds item to cart
5. Proceeds to checkout
6. Selects/adds delivery address
7. Places order (Cash on Delivery for demo)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_use import Agent, Browser
from browser_use import ChatOpenAI, ChatAnthropic

from config import (
    BLINKIT_URL,
    BLINKIT_EMAIL,
    BLINKIT_PASSWORD,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
)


def get_llm():
    if LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=ANTHROPIC_API_KEY,
            temperature=0.3,
        )
    return ChatOpenAI(
        model="gpt-4o",
        api_key=OPENAI_API_KEY,
        temperature=0.3,
    )


async def run_order_agent(
    item_to_order: str,
):
    """
    Run the order agent that navigates BlinkIt and places an order.

    Args:
        item_to_order: What to search for and order (e.g. "chocolate", "flowers", "chips")
    """
    print(f"\n{'='*60}")
    print(f"  ORDER AGENT STARTING")
    print(f"  Platform: BlinkIt Clone")
    print(f"  Item to order: {item_to_order}")
    print(f"{'='*60}\n")

    llm = get_llm()

    browser = Browser(
        headless=False,  # Visible for demo!
    )

    # Full task for the order agent — one comprehensive instruction
    order_task = f"""
You are an AI agent placing a grocery order on BlinkIt (a grocery delivery app).

STEP 1 — LOGIN (DO THIS FIRST, BEFORE ANYTHING ELSE):
Go to {BLINKIT_URL}
Look for a Login or Sign In option. Click it.
Enter email: {BLINKIT_EMAIL}
Enter password: {BLINKIT_PASSWORD}
Submit the login form and wait for the home page to load.
You MUST be fully logged in before proceeding. Confirm you see the logged-in home page with products.

STEP 2 — SEARCH FOR ITEM:
Find the search bar on the page (usually at the top).
Type "{item_to_order}" in the search bar and press Enter or click the search button.
IMPORTANT: After typing the product name, WAIT 5 SECONDS for search results to load. The search is slow. Use the "wait" action for 5 seconds. Do NOT click or do anything until the results have appeared.

STEP 3 — ADD TO CART:
From the search results, find a suitable product that matches "{item_to_order}".
Click the "Add" or "Add to Cart" button on that product.
If there's a quantity selector, keep it at 1.
You should see the cart update (cart icon shows 1 item).

STEP 4 — GO TO CART / CHECKOUT:
Click on the cart icon or "View Cart" or "Checkout" button.
You should see your cart with the item you added.
Proceed to checkout.

STEP 5 — SELECT ADDRESS:
On the checkout page, you need a delivery address.
Select an existing address from the list. Just click on the first available address.
DO NOT try to add a new address. DO NOT click "Add Address". Only use an address that already exists.

STEP 6 — PLACE ORDER:
Select "Cash on Delivery" as the payment method.
NEVER select online payment or Stripe. ALWAYS choose Cash on Delivery (COD).
Click the final "Place Order" or "Confirm Order" button.
Wait for the order confirmation page.

IMPORTANT:
- You MUST login first before searching. Do not skip login.
- After searching, WAIT 5 SECONDS for results. Do not rush.
- NEVER add a new address. Only select an existing one.
- ALWAYS use Cash on Delivery. Never use online payment.
- If a step fails, try again once before reporting the error.
- The goal is to successfully place the order. Report the final status.
"""

    print(f"[Order Agent] Starting browser and navigating to BlinkIt...")

    agent = Agent(
        task=order_task,
        llm=llm,
        browser=browser,
    )

    result = await agent.run()

    print(f"\n{'='*60}")
    print(f"  ORDER AGENT COMPLETE")
    print(f"  Result: {result}")
    print(f"{'='*60}\n")

    await browser.close()
    return result


if __name__ == "__main__":
    asyncio.run(
        run_order_agent(
            item_to_order="chocolate",
        )
    )
