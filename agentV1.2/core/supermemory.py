import logging
import os

from config import config

logger = logging.getLogger(__name__)


class SuperMemory:
    """Loads user personality, chat style, guardrails, and ordering rules from markdown file."""

    def __init__(self):
        self.content: str = ""
        self.price_cap: int = 500
        self._load()

    def _load(self):
        path = config.SUPERMEMORY_PATH
        if not os.path.exists(path):
            logger.warning(f"SuperMemory not found at {path}")
            self.content = "No supermemory configured. Chat naturally and helpfully."
            return

        with open(path, "r") as f:
            self.content = f.read()

        # Extract price cap
        for line in self.content.split("\n"):
            if "price cap" in line.lower() and "₹" in line:
                try:
                    import re
                    match = re.search(r"₹(\d+)", line)
                    if match:
                        self.price_cap = int(match.group(1))
                except (ValueError, AttributeError):
                    pass

        logger.info(f"SuperMemory loaded ({len(self.content)} chars, price cap: ₹{self.price_cap})")

    def get_personality_prompt(self) -> str:
        return self.content

    def get_price_cap(self) -> int:
        return self.price_cap

    def reload(self):
        self._load()
