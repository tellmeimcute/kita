

import asyncio
from logging import getLogger
from typing import Callable, Sequence
from dishka import AsyncContainer
from .base import KitaEvent

logger = getLogger("kita.event")

class EventBus:
    def __init__(self, container: AsyncContainer):
        self._container = container
        self.listeners = {}

        self.background_tasks = set()

    def sub(self, event: type[KitaEvent], listener: Callable):
        event_name = event.__name__

        if not self.listeners.get(event_name):
            self.listeners[event_name] = {listener}
        else:
            self.listeners[event_name].add(listener)

        logger.debug("Event %s sub to %s listener", event_name, listener.__name__)

    def unsub(self, event: type[KitaEvent], listener: Callable):
        event_name = event.__name__

        self.listeners[event_name].discard(listener)
        if len(self.listeners[event_name]) == 0:
            del self.listeners[event_name]

        logger.debug("Event %s unsub %s listener", event_name, listener.__name__)

    async def _run_listener(self, listener: Callable, event: KitaEvent):
        try:
            async with self._container() as container:
                await listener(event, container)
        except Exception as e:
            logger.error("Listener %s failed: %s", listener.__name__, e, exc_info=True)

    async def _dispatch(self, listeners: Sequence, event: KitaEvent):
        async with asyncio.TaskGroup() as tg:
            for listener in listeners:
                tg.create_task(self._run_listener(listener, event))

    def dispatch(self, event: KitaEvent):
        event_name = event.__class__.__name__
        listeners = self.listeners.get(event_name, [])

        task = asyncio.create_task(self._dispatch(listeners, event))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

        logger.debug("Event %s dispatched to %s listeners", event_name, len(listeners))
        