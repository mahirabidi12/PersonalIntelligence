import logging
import os

from config import config

logger = logging.getLogger(__name__)


class SuperMemory:
    """
    Loads and provides the user's personality training data.
    Reads from supermemory.md — the user's chat style, guardrails,
    price caps, and personality traits.
    """

    def __init__(self):
        self.content: str = ""
        self.price_cap: int = 500  # Default ₹500
        self._load()

    def _load(self):
        """Load supermemory from markdown file."""
        path = config.SUPERMEMORY_PATH
        if not os.path.exists(path):
            logger.warning(f"SuperMemory file not found at {path}")
            self.content = "No supermemory configured. Chat naturally."
            return

        with open(path, "r") as f:
            self.content = f.read()

        # Extract price cap if present
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
        """Get the full supermemory as a prompt section."""
        return self.content

    def get_price_cap(self) -> int:
        """Get the max order price."""
        return self.price_cap

    def reload(self):
        """Reload supermemory from disk (for live updates)."""
        self._load()
