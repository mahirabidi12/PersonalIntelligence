"""
SuperAgent v0 — Entry Point

Run with:
    python main.py

Or with a specific task:
    python main.py "I'm busy from 2-3pm. Talk to Ananya like me on WhatsApp. Also order some chocolate from BlinkIt."
"""

import asyncio
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import run_orchestrator


DEFAULT_TASK = (
    "I am busy from 2-3 pm in a meeting, but my girlfriend Ananya is going to text me. "
    "I want you to talk to Ananya on WhatsApp the way I would. "
    "Also, order some chocolate for her from BlinkIt."
)


async def main():
    # Get task from command line args or use default
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("\n  No task provided. Using default demo task.\n")
        print(f"  Tip: python main.py \"your task here\"\n")
        task = DEFAULT_TASK

    await run_orchestrator(task)


if __name__ == "__main__":
    asyncio.run(main())
