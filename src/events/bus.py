from collections.abc import Sequence

from loguru import logger

from interfaces import EventListenerProtocol

from .base import Event


class EventBus:
    """In-process pub/sub for domain events.

    While a transaction is open (``begin`` was called by the unit of work) events are
    buffered and dispatched only after the COMMIT. A rollback throws the buffer away.
    """

    __slots__ = ("_depth", "_listeners", "_pending")

    def __init__(self, listeners: Sequence[EventListenerProtocol]):
        self._listeners: dict[type[Event], list[EventListenerProtocol]] = {}
        for listener in listeners:
            self.subscribe(listener)

        self._pending: list[Event] = []
        self._depth = 0

    @property
    def deferred(self) -> bool:
        return self._depth > 0

    def subscribe(self, listener: EventListenerProtocol) -> None:
        self._listeners.setdefault(listener.event_type, []).append(listener)

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
        listeners = self._listeners.get(type(event), ())
        logger.debug("Dispatch {} to {} listener(s)", event, len(listeners))

        for listener in listeners:
            try:
                await listener.handle(event)
            except Exception:
                logger.exception(
                    "Listener {} failed on {}",
                    type(listener).__name__,
                    event,
                )
