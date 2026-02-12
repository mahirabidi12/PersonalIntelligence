"""
Style Loader — Pulls chat history from Supabase and builds a system prompt
that teaches the LLM to text like the user (Saswata / user1).
"""

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, WHATSAPP_USER_ID


def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def fetch_chat_history(user_id: str = WHATSAPP_USER_ID, limit: int = 200) -> list[dict]:
    """Fetch recent messages sent BY the user to learn their texting style."""
    client = get_supabase_client()
    result = (
        client.table("chats")
        .select("content, conversation_id, created_at")
        .eq("sender_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []


def fetch_conversation_history(conversation_id: str, limit: int = 50) -> list[dict]:
    """Fetch full conversation history for a specific chat."""
    client = get_supabase_client()
    result = (
        client.table("chats")
        .select("sender_id, content, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []


def build_style_prompt(user_id: str = WHATSAPP_USER_ID) -> str:
    """
    Analyze the user's past messages and build a system prompt
    that instructs the LLM to mimic their texting style.
    """
    messages = fetch_chat_history(user_id, limit=200)

    if not messages:
        return (
            "You are texting on behalf of the user. "
            "Use a casual, friendly tone. Keep messages short and natural."
        )

    # Extract just the message content
    user_texts = [m["content"] for m in messages]

    # Analyze style patterns
    avg_length = sum(len(t) for t in user_texts) / len(user_texts)
    uses_emoji = any(
        any(ord(c) > 127 for c in t) for t in user_texts
    )
    uses_exclamation = sum(1 for t in user_texts if "!" in t) / len(user_texts)

    # Build example messages block
    examples = "\n".join(f"  - \"{t}\"" for t in user_texts[:30])

    style_prompt = f"""You are impersonating a person in a WhatsApp chat. You must text EXACTLY like them.

STYLE ANALYSIS:
- Average message length: ~{int(avg_length)} characters
- Uses emoji: {"Yes" if uses_emoji else "Rarely"}
- Exclamation frequency: {int(uses_exclamation * 100)}% of messages
- Tone: Casual, friendly, direct

EXAMPLE MESSAGES FROM THIS PERSON:
{examples}

RULES:
1. Match the message length — don't write essays if they send short texts
2. Match their punctuation style and capitalization
3. Match their emoji usage (or lack thereof)
4. Use similar slang and phrases they use
5. Be natural — you ARE this person right now
6. Never reveal you are an AI or agent
7. If you don't know something specific about the person's life, be vague but natural
8. Keep the conversation flowing — ask questions back, react naturally"""

    return style_prompt


if __name__ == "__main__":
    # Test: print the generated style prompt
    prompt = build_style_prompt()
    print(prompt)
