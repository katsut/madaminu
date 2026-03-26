import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def on(self, event_type: type, handler: Callable):
        self._handlers[event_type].append(handler)

    async def emit(self, event: Any):
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                asyncio.create_task(handler(event))
            except Exception:
                logger.exception("Event handler failed: %s", handler.__name__)
