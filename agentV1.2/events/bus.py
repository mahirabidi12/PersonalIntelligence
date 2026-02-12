import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventBus:
    """Async event bus with queue-based dispatch and WebSocket broadcast support."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)
        self._ws_listeners: list[Callable] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self.event_log: list[dict] = []

    def subscribe(self, event_type: str, callback: Callable[..., Coroutine]):
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to '{event_type}': {callback.__name__}")

    def add_ws_listener(self, callback: Callable):
        """Add a WebSocket listener for live event broadcasting."""
        self._ws_listeners.append(callback)

    def remove_ws_listener(self, callback: Callable):
        self._ws_listeners = [c for c in self._ws_listeners if c != callback]

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None):
        event = {
            "event_type": event_type,
            "payload": payload or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue.put(event)
        self.event_log.append(event)
        if len(self.event_log) > 200:
            self.event_log = self.event_log[-100:]

        # Broadcast to WebSocket listeners
        for listener in self._ws_listeners:
            try:
                await listener(event)
            except Exception:
                pass

        logger.info(f"Event: {event_type} | {payload}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())
        logger.info("EventBus started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _dispatch_loop(self):
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                for callback in self._subscribers.get(event["event_type"], []):
                    try:
                        await callback(event["payload"])
                    except Exception as e:
                        logger.error(f"Subscriber error for {event['event_type']}: {e}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"EventBus dispatch error: {e}")
