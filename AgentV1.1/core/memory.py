import json
import logging
import os
from datetime import datetime
from typing import Optional

import aiosqlite

from models.schemas import ChatMessage

logger = logging.getLogger(__name__)


class Memory:
    """SQLite-backed conversation history and user state."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init_db(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sender_name TEXT DEFAULT '',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    input_data TEXT DEFAULT '',
                    output_data TEXT DEFAULT '',
                    status TEXT DEFAULT 'ok',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info(f"Memory initialized at {self.db_path}")

    async def save_message(self, role: str, message: str, sender_name: str = ""):
        """Store a conversation message."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (role, message, sender_name) VALUES (?, ?, ?)",
                (role, message, sender_name),
            )
            await db.commit()

    async def get_recent_messages(self, limit: int = 20) -> list[ChatMessage]:
        """Get the last N messages."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, message, sender_name, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            messages = [
                ChatMessage(
                    role=row["role"],
                    content=row["message"],
                    sender_name=row["sender_name"],
                    timestamp=row["timestamp"] or "",
                )
                for row in reversed(rows)
            ]
            return messages

    async def get_conversation_context(self, limit: int = 10) -> str:
        """Get formatted conversation context string for LLM."""
        messages = await self.get_recent_messages(limit)
        lines = []
        for msg in messages:
            name = msg.sender_name or msg.role
            lines.append(f"{name}: {msg.content}")
        return "\n".join(lines)

    async def get_state(self, key: str) -> Optional[str]:
        """Get a user state value."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM user_state WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_state(self, key: str, value: str):
        """Set a user state value."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat()),
            )
            await db.commit()

    async def log_action(
        self, agent_name: str, action: str, input_data: str = "", output_data: str = "", status: str = "ok"
    ):
        """Log an agent action."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO agent_logs (agent_name, action, input_data, output_data, status) VALUES (?, ?, ?, ?, ?)",
                (agent_name, action, input_data, output_data, status),
            )
            await db.commit()

    async def get_recent_logs(self, limit: int = 50) -> list[dict]:
        """Get recent agent logs."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT agent_name, action, input_data, output_data, status, timestamp FROM agent_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in reversed(rows)]
