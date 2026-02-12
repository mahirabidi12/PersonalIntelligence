import logging
import os
from datetime import datetime
from typing import Optional

import aiosqlite

from models.schemas import ChatMessage, AgentLog

logger = logging.getLogger(__name__)


class Memory:
    """SQLite-backed conversation history, agent logs, and task state."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def init_db(self):
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
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    status TEXT DEFAULT 'ok',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE,
                    task_type TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    result TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info(f"Memory initialized at {self.db_path}")

    async def save_message(self, role: str, message: str, sender_name: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (role, message, sender_name) VALUES (?, ?, ?)",
                (role, message, sender_name),
            )
            await db.commit()

    async def get_recent_messages(self, limit: int = 20) -> list[ChatMessage]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, message, sender_name, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                ChatMessage(role=r["role"], content=r["message"], sender_name=r["sender_name"], timestamp=r["timestamp"] or "")
                for r in reversed(rows)
            ]

    async def log_action(self, agent_name: str, action: str, detail: str = "", status: str = "ok"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO agent_logs (agent_name, action, detail, status) VALUES (?, ?, ?, ?)",
                (agent_name, action, detail, status),
            )
            await db.commit()

    async def get_recent_logs(self, limit: int = 100) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT agent_name, action, detail, status, timestamp FROM agent_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in reversed(rows)]

    async def save_task(self, task_id: str, task_type: str, description: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO tasks (task_id, task_type, description) VALUES (?, ?, ?)",
                (task_id, task_type, description),
            )
            await db.commit()

    async def update_task(self, task_id: str, status: str, result: str = "", error: str = ""):
        async with aiosqlite.connect(self.db_path) as db:
            completed_at = datetime.now().isoformat() if status in ("completed", "failed") else None
            await db.execute(
                "UPDATE tasks SET status=?, result=?, error=?, completed_at=? WHERE task_id=?",
                (status, result, error, completed_at, task_id),
            )
            await db.commit()

    async def get_tasks(self, limit: int = 20) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
            )
            return [dict(r) for r in await cursor.fetchall()]

    async def get_state(self, key: str) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM user_state WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_state(self, key: str, value: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat()),
            )
            await db.commit()
