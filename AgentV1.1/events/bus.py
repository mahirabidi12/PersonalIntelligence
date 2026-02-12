import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventBus:
    """Async event bus using asyncio.Queue. Interface designed for easy Redis swap later."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: str, callback: Callable[..., Coroutine]):
        """Register an async callback for an event type."""
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to '{event_type}': {callback.__name__}")

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None):
        """Publish an event to the bus."""
        event = {
            "event_type": event_type,
            "payload": payload or {},
            "timestamp": datetime.now().isoformat(),
        }
        await self._queue.put(event)
        logger.info(f"Published event: {event_type} | {payload}")

    async def start(self):
        """Start the event dispatcher loop."""
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop())
        logger.info("EventBus started")

    async def stop(self):
        """Stop the event dispatcher."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")

    async def _dispatch_loop(self):
        """Consume events from queue and dispatch to subscribers."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                event_type = event["event_type"]
                payload = event["payload"]

                callbacks = self._subscribers.get(event_type, [])
                if not callbacks:
                    logger.warning(f"No subscribers for event: {event_type}")
                    continue

                for callback in callbacks:
                    try:
                        await callback(payload)
                    except Exception as e:
                        logger.error(f"Error in subscriber {callback.__name__} for {event_type}: {e}")

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"EventBus dispatch error: {e}")
