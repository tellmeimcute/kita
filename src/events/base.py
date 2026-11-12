from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Event:
    """Domain event.

    ``bot_id`` is the tenant — the bot in whose context the event happened.
    """

    bot_id: int


class EventListener[T](ABC):
    """Subscribes to a single event type: ``event_type`` declares the subscription."""

    event_type: ClassVar[type]

    @abstractmethod
    async def handle(self, event: T) -> None: ...
