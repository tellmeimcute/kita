

import asyncio
from logging import getLogger
from typing import Coroutine
from dishka import AsyncContainer
from .base import KitaEvent

logger = getLogger("kita.event")

class EventBus:
    def __init__(self, container: AsyncContainer):
        self._container = container
        self.listeners = {}

    def sub(self, event: type[KitaEvent], listener: Coroutine):
        event_name = event.__name__

        if not self.listeners.get(event):
            self.listeners[event_name] = {listener}
        else:
            self.listeners[event_name].add(listener)

        logger.debug("Event %s sub to %s listener", event_name, listener.__name__)

    def unsub(self, event: type[KitaEvent], listener: Coroutine):
        event_name = event.__name__

        self.listeners[event_name].remove(listener)
        if len(self.listeners[event_name]) == 0:
            del self.listeners[event_name]

        logger.debug("Event %s unsub %s listener", event_name, listener.__name__)

    async def dispatch(self, event: KitaEvent):
        event_name = event.__class__.__name__

        listeners = self.listeners.get(event_name, [])
        async with self._container() as container:
            for listener in listeners:
                asyncio.create_task(listener(event, container))
        
        logger.debug("Event %s dispatched to %s listeners", event_name, len(listeners))