"""
Orchestrator — Takes a natural language task and decomposes it into sub-tasks.

Uses an LLM to parse the user's request and determine:
1. Who to chat with (contact name)
2. How long to chat (duration)
3. What to order (item)
4. Any delivery details

Then runs the appropriate agents concurrently.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY


DECOMPOSITION_PROMPT = """You are a task decomposition AI. The user will give you a natural language instruction about tasks they want an AI agent to perform on their behalf.

You need to extract structured sub-tasks from the instruction.

There are two types of sub-tasks:
1. CHAT — The user wants the agent to chat with someone on WhatsApp on their behalf
2. ORDER — The user wants the agent to order something from BlinkIt (grocery delivery)

For each sub-task, extract the relevant parameters.

Respond in JSON format ONLY (no markdown, no explanation):

{
  "tasks": [
    {
      "type": "chat",
      "contact_name": "name of the person to chat with",
      "duration_minutes": 30,
      "context": "any special instructions about how to chat, topics, etc."
    },
    {
      "type": "order",
      "item": "what to order",
      "delivery_address": {
        "address_line": "address if mentioned",
        "city": "city if mentioned",
        "state": "state if mentioned",
        "pincode": "pincode if mentioned",
        "mobile": "phone if mentioned"
      }
    }
  ]
}

Rules:
- If no duration is specified for chat, default to 30 minutes
- If no address is specified for order, set delivery_address to null
- Extract the contact name as mentioned (e.g., "girlfriend" → use the actual name if given, otherwise "girlfriend")
- The item to order should be specific if mentioned, otherwise use the general description
- You can have multiple tasks of the same type

User instruction:
"""


async def decompose_task(user_instruction: str) -> dict:
    """
    Use LLM to decompose a natural language task into structured sub-tasks.
    """
    if LLM_PROVIDER == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": DECOMPOSITION_PROMPT + user_instruction,
                }
            ],
        )
        raw = response.content[0].text
    else:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a task decomposition assistant. Respond only in valid JSON.",
                },
                {
                    "role": "user",
                    "content": DECOMPOSITION_PROMPT + user_instruction,
                },
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content

    # Parse the JSON response
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # remove first line
        raw = raw.rsplit("```", 1)[0]  # remove last fence
    raw = raw.strip()

    return json.loads(raw)


async def run_orchestrator(user_instruction: str):
    """
    Main orchestrator: decompose task → launch agents concurrently.
    """
    from agents.chat_agent import run_chat_agent
    from agents.order_agent import run_order_agent

    print(f"\n{'='*60}")
    print(f"  SUPER AGENT ORCHESTRATOR")
    print(f"{'='*60}")
    print(f"\n  Task: {user_instruction}\n")
    print(f"  Decomposing task with LLM...\n")

    plan = await decompose_task(user_instruction)
    tasks = plan.get("tasks", [])

    print(f"  Found {len(tasks)} sub-task(s):")
    for i, task in enumerate(tasks):
        print(f"    {i+1}. [{task['type'].upper()}] ", end="")
        if task["type"] == "chat":
            print(f"Chat with {task['contact_name']} for {task['duration_minutes']}min")
        elif task["type"] == "order":
            print(f"Order '{task['item']}' from BlinkIt")
    print()

    # Build async tasks
    coroutines = []

    for task in tasks:
        if task["type"] == "chat":
            coroutines.append(
                run_chat_agent(
                    contact_name=task["contact_name"],
                    duration_minutes=task.get("duration_minutes", 30),
                    check_interval_seconds=10,
                )
            )
        elif task["type"] == "order":
            coroutines.append(
                run_order_agent(
                    item_to_order=task["item"],
                )
            )

    if not coroutines:
        print("  No actionable tasks found. Exiting.")
        return

    print(f"  Launching {len(coroutines)} agent(s) concurrently...\n")
    print(f"{'='*60}\n")

    # Run all agents concurrently
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    print(f"\n{'='*60}")
    print(f"  ALL AGENTS COMPLETE")
    print(f"{'='*60}")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  Agent {i+1}: FAILED — {result}")
        else:
            print(f"  Agent {i+1}: SUCCESS")
    print()

    return results
