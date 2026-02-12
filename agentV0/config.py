import os
from dotenv import load_dotenv

load_dotenv()

# LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# WhatsApp Clone
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://whatsapp-rl-clone.vercel.app/")
WHATSAPP_USER_ID = os.getenv("WHATSAPP_USER_ID", "user1")
WHATSAPP_USER_NAME = os.getenv("WHATSAPP_USER_NAME", "Saswata")

# BlinkIt Clone
BLINKIT_URL = os.getenv("BLINKIT_URL", "https://binkeyit-full-stack-ydrn.vercel.app/")
BLINKIT_EMAIL = os.getenv("BLINKIT_EMAIL", "")
BLINKIT_PASSWORD = os.getenv("BLINKIT_PASSWORD", "")
