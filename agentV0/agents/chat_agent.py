"""
Chat Agent — Uses browser-use to operate the WhatsApp clone.

Uses a SINGLE persistent agent that:
1. Opens browser → logs in as Saswata
2. Opens Ananya's chat
3. Monitors for new messages continuously
4. When a message arrives, replies in Saswata's texting style
5. Keeps watching until time runs out
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_use import Agent, Browser
from browser_use import ChatOpenAI, ChatAnthropic

from config import (
    WHATSAPP_URL,
    WHATSAPP_USER_ID,
    WHATSAPP_USER_NAME,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
)
from style.style_loader import build_style_prompt


def get_llm():
    if LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=ANTHROPIC_API_KEY,
            temperature=0.7,
        )
    return ChatOpenAI(
        model="gpt-4o",
        api_key=OPENAI_API_KEY,
        temperature=0.7,
    )


async def run_chat_agent(
    contact_name: str,
    duration_minutes: int = 30,
    check_interval_seconds: int = 10,
):
    """
    Run a single persistent chat agent that monitors and replies on WhatsApp clone.

    Args:
        contact_name: Name of the contact to chat with (e.g. "Ananya")
        duration_minutes: How long to keep the agent running
        check_interval_seconds: How often to check for new messages
    """
    print(f"\n{'='*60}")
    print(f"  CHAT AGENT STARTING")
    print(f"  Chatting as: {WHATSAPP_USER_NAME} ({WHATSAPP_USER_ID})")
    print(f"  Target contact: {contact_name}")
    print(f"  Duration: {duration_minutes} minutes")
    print(f"{'='*60}\n")

    # Build the style prompt from chat history
    style_prompt = build_style_prompt(WHATSAPP_USER_ID)
    print("[Style] Loaded user texting style from chat history.\n")

    llm = get_llm()

    browser = Browser(
        headless=False,
        keep_alive=True,
    )

    # ONE single comprehensive task for the entire session
    task = f"""You are an AI agent operating WhatsApp on behalf of {WHATSAPP_USER_NAME}.

PHASE 1 — LOGIN:
1. Go to {WHATSAPP_URL}
2. You will see a user selection screen with radio buttons. Select "{WHATSAPP_USER_NAME}" (the one labeled "User 1" or "{WHATSAPP_USER_ID}").
3. Click the "Enter Chat" button to log in.
4. You should now see the WhatsApp chat interface.

PHASE 2 — OPEN CHAT:
5. In the contacts list on the left, find and click on "{contact_name}".
6. The conversation with {contact_name} should now be open on the right side.
7. Note the last message in the chat and who sent it.

PHASE 3 — MONITOR AND REPLY (THIS IS YOUR MAIN JOB):
Now you must continuously monitor this conversation. Your job is to keep watching for new messages from {contact_name} and reply as {WHATSAPP_USER_NAME}.

Here is how {WHATSAPP_USER_NAME} texts — you MUST match this style exactly:
{style_prompt}

MONITORING RULES:
- Look at the LAST message in the chat area.
- If the last message is from {contact_name} (appears on the LEFT side, white background), you need to reply.
- If the last message is from you/{WHATSAPP_USER_NAME} (appears on the RIGHT side, green background), then {contact_name} hasn't responded yet — use the "wait" action to wait {check_interval_seconds} seconds, then check again.
- After sending a reply, use the "wait" action to wait {check_interval_seconds} seconds, then check again for their response.

TO REPLY:
1. Read the last few messages for context
2. Think of a natural reply matching the style above
3. Click on the message input box at the bottom (placeholder: "Type a message")
4. Type your reply
5. Press Enter to send

CRITICAL RULES:
- NEVER reveal you are an AI. You ARE {WHATSAPP_USER_NAME}.
- Only send ONE message per reply. Don't double-text.
- After sending, ALWAYS wait and check for the next message. Do NOT mark the task as done.
- Keep monitoring for the entire session. Use "wait" actions between checks.
- This task runs for {duration_minutes} minutes. Do NOT call "done" until you have been monitoring for that long.
- If there's nothing new, just wait {check_interval_seconds} seconds and check again. Be patient.
"""

    print(f"[Chat Agent] Launching single persistent agent...")
    print(f"[Chat Agent] Will monitor for {duration_minutes} minutes.\n")

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        max_steps=500,
    )

    result = await agent.run()

    print(f"\n{'='*60}")
    print(f"  CHAT AGENT SESSION COMPLETE")
    print(f"  Result: {result}")
    print(f"{'='*60}\n")

    await browser.close()
    return result


if __name__ == "__main__":
    asyncio.run(
        run_chat_agent(
            contact_name="Ananya",
            duration_minutes=30,
            check_interval_seconds=10,
        )
    )
