from collections.abc import Iterable

from interfaces import EventListenerProtocol

ListenerEntry = type[EventListenerProtocol] | EventListenerProtocol


class ListenerRegistry:
    __slots__ = ("_entries",)

    def __init__(self, entries: Iterable[ListenerEntry] = ()) -> None:
        self._entries: list[ListenerEntry] = []

        for entry in entries:
            self.add(entry)

    def add(self, entry: ListenerEntry) -> None:
        if entry not in self._entries:
            self._entries.append(entry)

    def entries_for(self, event_type: type) -> tuple[ListenerEntry, ...]:
        return tuple(entry for entry in self._entries if entry.event_type is event_type)

    def entries(self) -> tuple[ListenerEntry, ...]:
        return tuple(self._entries)
