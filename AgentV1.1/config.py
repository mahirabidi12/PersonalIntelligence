import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


@dataclass
class Config:
    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-5.2")

    # Supabase (WhatsApp clone DB)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # Deployed app URLs
    WHATSAPP_URL: str = os.getenv("WHATSAPP_URL", "https://whatsapp-rl-clone.vercel.app/")
    BLINKIT_URL: str = os.getenv("BLINKIT_URL", "https://binkeyit-full-stack-ydrn.vercel.app/")

    # WhatsApp agent config — Agent IS you (Saswata), chatting with your GF (Ananya)
    WHATSAPP_USER_ID: str = os.getenv("WHATSAPP_USER_ID", "user1")  # The login ID (user1, user2, etc.)
    WHATSAPP_AGENT_USER: str = os.getenv("WHATSAPP_AGENT_USER", "Saswata")  # Display name
    WHATSAPP_TARGET_CONTACT: str = os.getenv("WHATSAPP_TARGET_CONTACT", "Ananya")
    WHATSAPP_TARGET_ID: str = os.getenv("WHATSAPP_TARGET_ID", "user2")  # Target's login ID

    # BlinkeyIt login credentials
    BLINKIT_EMAIL: str = os.getenv("BLINKIT_EMAIL", "agent@test.com")
    BLINKIT_PASSWORD: str = os.getenv("BLINKIT_PASSWORD", "password123")

    # Agent settings
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "5"))
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"

    # Database
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "memory.db"))

    # SuperMemory path
    SUPERMEMORY_PATH: str = os.getenv(
        "SUPERMEMORY_PATH", os.path.join(os.path.dirname(__file__), "supermemory.md")
    )

    # Other contacts (non-GF) — agent sends one-shot replies during idle time
    CONTACTS: dict = field(default_factory=lambda: {
        "user3": "Arjun Mehta",
        "user4": "Priya Sharma",
        "user5": "Vikram Patel",
        "user6": "Neha Gupta",
        "user7": "Amit Kumar",
        "user8": "Rohan Singh",
        "user9": "Kavita Reddy",
        "user10": "Dev Team",
        "user11": "Sanjay Iyer",
    })

    # Initial instruction — what the user tells the agent before leaving
    INITIAL_INSTRUCTION: str = os.getenv(
        "INITIAL_INSTRUCTION",
        "My girlfriend will text me. Talk to her like I would. If she wants food, order it.",
    )


config = Config()
