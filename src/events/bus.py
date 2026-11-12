from loguru import logger

from interfaces import EventListenerProtocol, ListenerResolverProtocol

from .base import Event
from .registry import ListenerEntry, ListenerRegistry


class EventBus:
    """In-process pub/sub for domain events.

    While a transaction is open (``begin`` was called by the unit of work) events are
    buffered and dispatched only after the COMMIT. A rollback throws the buffer away.

    Listeners come from a :class:`ListenerRegistry`
    """

    __slots__ = ("_depth", "_pending", "_registry", "_resolver")

    def __init__(self, registry: ListenerRegistry, resolver: ListenerResolverProtocol):
        self._registry = registry
        self._resolver = resolver
        self._pending: list[Event] = []
        self._depth = 0

    @property
    def deferred(self) -> bool:
        return self._depth > 0

    def begin(self) -> None:
        self._depth += 1

    def end(self) -> None:
        self._depth = max(self._depth - 1, 0)

    async def publish(self, event: Event) -> None:
        if self.deferred:
            logger.debug("Event deferred: {}", event)
            self._pending.append(event)
            return

        await self._dispatch(event)

    async def flush(self) -> None:
        pending, self._pending = self._pending, []

        for event in pending:
            await self._dispatch(event)

    def discard(self) -> None:
        self._pending.clear()

    async def _dispatch(self, event: Event) -> None:
        entries = self._registry.entries_for(type(event))
        logger.debug("Dispatch {} to {} listener(s)", event, len(entries))

        for entry in entries:
            try:
                listener = await self._resolve(entry)
                await listener.handle(event)
            except Exception:
                logger.exception("Listener {} failed on {}", _label(entry), event)

    async def _resolve(self, entry: ListenerEntry) -> EventListenerProtocol:
        if isinstance(entry, type):
            return await self._resolver.get(entry)

        return entry


def _label(entry: ListenerEntry) -> str:
    return entry.__name__ if isinstance(entry, type) else type(entry).__name__
