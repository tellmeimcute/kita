from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from events.base import Event


class EventBusProtocol(Protocol):
    """Pub/sub of domain events.

    ``begin``/``end``/``flush``/``discard`` are driven by the unit of work: while a
    transaction is open events are buffered and dispatched only after the COMMIT.
    """

    async def publish(self, event: "Event") -> None: ...

    async def flush(self) -> None: ...

    def discard(self) -> None: ...

    def begin(self) -> None: ...

    def end(self) -> None: ...


class EventListenerProtocol(Protocol):
    """A subscriber. ``event_type`` decides which events reach ``handle``."""

    event_type: type

    async def handle(self, event: "Event") -> None: ...
