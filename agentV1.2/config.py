import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


@dataclass
class Config:
    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")

    # App URLs (our deployed clones)
    WHATSAPP_URL: str = os.getenv(
        "WHATSAPP_URL", "https://browser-agent-8.preview.emergentagent.com"
    )
    BLINKIT_URL: str = os.getenv(
        "BLINKIT_URL", "https://browser-agent-8.preview.emergentagent.com"
    )

    # WhatsApp agent config
    WHATSAPP_LOGIN_EMAIL: str = os.getenv("WHATSAPP_LOGIN_EMAIL", "saswata@whatsapp2.com")
    WHATSAPP_LOGIN_PASSWORD: str = os.getenv("WHATSAPP_LOGIN_PASSWORD", "password123")
    WHATSAPP_AGENT_USER: str = os.getenv("WHATSAPP_AGENT_USER", "Saswata")
    WHATSAPP_TARGET_CONTACT: str = os.getenv("WHATSAPP_TARGET_CONTACT", "Ananya")

    # Blinkit agent config
    BLINKIT_EMAIL: str = os.getenv("BLINKIT_EMAIL", "demo@blinkit2.com")
    BLINKIT_PASSWORD: str = os.getenv("BLINKIT_PASSWORD", "password123")

    # Agent settings
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "8"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))

    # Paths
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "memory.db"))
    SUPERMEMORY_PATH: str = os.getenv(
        "SUPERMEMORY_PATH", os.path.join(os.path.dirname(__file__), "supermemory.md")
    )
    SCREENSHOT_DIR: str = os.path.join(os.path.dirname(__file__), "data", "screenshots")

    # Initial instruction
    INITIAL_INSTRUCTION: str = os.getenv(
        "INITIAL_INSTRUCTION",
        "My girlfriend will text me. Talk to her like I would. If she wants food, order it from Blinkit.",
    )

    # Agent API port (separate from main app)
    AGENT_PORT: int = int(os.getenv("AGENT_PORT", "8100"))


config = Config()
