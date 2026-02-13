"""
Step Logger — Production-quality action logs for LLM training data.

Writes only meaningful agent steps to log.txt:
  - UI interactions (click, type, navigate, scroll)
  - Visual observations (found element, saw color, read text)
  - Reasoning & decisions (intent classification, option selection)
  - State transitions (page loaded, order placed, error encountered)

Each log entry is a single structured line capturing:
  TIMESTAMP | AGENT | STEP_TYPE | action description | context/details

These logs are designed to be parsed and used as training data for
teaching another LLM how to perform browser-based agent tasks.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional

# Resolve log path relative to AgentV1.1 root
_AGENT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(_AGENT_ROOT, "log.txt")

# Lock for thread-safe / async-safe writes
_write_lock = asyncio.Lock()


# Step types for structured training data
class StepType:
    OBSERVE = "OBSERVE"      # saw something on screen
    CLICK = "CLICK"          # clicked an element
    TYPE = "TYPE"            # typed text into a field
    NAVIGATE = "NAVIGATE"    # navigated to a URL or page section
    SCROLL = "SCROLL"        # scrolled the page
    WAIT = "WAIT"            # waited for something to load
    EXTRACT = "EXTRACT"      # extracted data from the page
    REASON = "REASON"        # LLM reasoning / decision point
    DECIDE = "DECIDE"        # chose between options
    SEND = "SEND"            # sent a message or request
    RECEIVE = "RECEIVE"      # received a message or response
    EVENT = "EVENT"          # system event (order placed, error, etc.)
    SEARCH = "SEARCH"        # searched for something
    SUBMIT = "SUBMIT"        # submitted a form or action


def _format_entry(
    agent: str,
    step_type: str,
    action: str,
    detail: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """Format a single log line for training data."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    parts = [ts, agent, step_type, action]
    if detail:
        parts.append(detail)
    line = " | ".join(parts)
    if run_id:
        line = f"[run:{run_id}] {line}"
    return line


async def log_step(
    agent: str,
    step_type: str,
    action: str,
    detail: Optional[str] = None,
    run_id: Optional[str] = None,
):
    """
    Append a single step entry to log.txt.

    Args:
        agent:     Name of the agent performing the step (e.g. "WhatsAppAgent")
        step_type: Category from StepType (e.g. StepType.CLICK)
        action:    Human-readable description of what happened
        detail:    Optional extra context (element selector, extracted value, etc.)
        run_id:    Optional run identifier to group steps from the same session
    """
    entry = _format_entry(agent, step_type, action, detail, run_id)
    async with _write_lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry + "\n")


def log_step_sync(
    agent: str,
    step_type: str,
    action: str,
    detail: Optional[str] = None,
    run_id: Optional[str] = None,
):
    """Synchronous version for non-async contexts."""
    entry = _format_entry(agent, step_type, action, detail, run_id)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


async def log_session_start(run_id: str):
    """Mark the beginning of a new agent session."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _write_lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"SESSION START | {ts} | run:{run_id}\n")
            f.write(f"{'='*80}\n")


async def log_session_end(run_id: str):
    """Mark the end of an agent session."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with _write_lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"SESSION END   | {ts} | run:{run_id}\n")
            f.write(f"{'='*80}\n\n")
