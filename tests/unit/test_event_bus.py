from dataclasses import dataclass

from events import Event, EventBus, EventListener, ListenerRegistry, SuggestionAccepted


@dataclass(frozen=True, slots=True)
class OtherEvent(Event):
    payload: str


class Recorder(EventListener[Event]):
    def __init__(self, event_type: type[Event]):
        self.event_type = event_type
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class TypeListener(EventListener[SuggestionAccepted]):
    """Subscribed as a type: the bus builds it from the request container."""

    event_type = SuggestionAccepted

    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class Broken(EventListener[Event]):
    event_type = SuggestionAccepted

    async def handle(self, event: Event) -> None:
        raise RuntimeError("broken listener")


class FakeResolver:
    """Stands in for the request container."""

    def __init__(self, instances: dict[type, EventListener] | None = None) -> None:
        self._instances = instances or {}

    async def get(self, key: type) -> EventListener:
        return self._instances[key]


def make_bus(*entries: EventListener | type) -> EventBus:
    return EventBus(ListenerRegistry(entries), FakeResolver())


def accepted(suggestion_id: int = 1) -> SuggestionAccepted:
    return SuggestionAccepted(bot_id=100, suggestion_id=suggestion_id)


async def test_publish_reaches_only_the_listener_of_the_event_type():
    suggestion = Recorder(SuggestionAccepted)
    other = Recorder(OtherEvent)
    bus = make_bus(suggestion, other)

    await bus.publish(accepted())

    assert suggestion.events == [accepted()]
    assert other.events == []


async def test_event_goes_to_every_listener_of_the_type():
    first = Recorder(SuggestionAccepted)
    second = Recorder(SuggestionAccepted)
    bus = make_bus(first, second)

    await bus.publish(accepted())

    assert first.events == second.events == [accepted()]


async def test_event_without_listeners_is_ignored():
    bus = make_bus()

    await bus.publish(accepted())


async def test_publish_inside_transaction_is_deferred_until_flush():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(recorder)

    bus.begin()
    await bus.publish(accepted())
    bus.end()

    assert recorder.events == []

    await bus.flush()

    assert recorder.events == [accepted()]


async def test_flush_keeps_the_publish_order():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(recorder)

    bus.begin()
    await bus.publish(accepted(1))
    await bus.publish(accepted(2))
    bus.end()
    await bus.flush()

    assert [event.suggestion_id for event in recorder.events] == [1, 2]


async def test_discard_drops_deferred_events():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(recorder)

    bus.begin()
    await bus.publish(accepted())
    bus.end()
    bus.discard()

    await bus.flush()

    assert recorder.events == []


async def test_flushed_events_are_not_dispatched_twice():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(recorder)

    bus.begin()
    await bus.publish(accepted())
    bus.end()

    await bus.flush()
    await bus.flush()

    assert recorder.events == [accepted()]


async def test_nested_begin_keeps_events_deferred():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(recorder)

    bus.begin()
    bus.begin()
    bus.end()
    await bus.publish(accepted())

    assert recorder.events == []

    bus.end()
    await bus.flush()

    assert recorder.events == [accepted()]


async def test_broken_listener_does_not_block_the_others():
    recorder = Recorder(SuggestionAccepted)
    bus = make_bus(Broken(), recorder)

    await bus.publish(accepted())

    assert recorder.events == [accepted()]


async def test_listener_added_after_the_bus_is_created_is_picked_up():
    registry = ListenerRegistry()
    bus = EventBus(registry, FakeResolver())
    recorder = Recorder(SuggestionAccepted)

    registry.add(recorder)
    await bus.publish(accepted())

    assert recorder.events == [accepted()]


async def test_a_listener_type_is_built_by_the_request_container():
    instance = TypeListener()
    bus = EventBus(ListenerRegistry([TypeListener]), FakeResolver({TypeListener: instance}))

    await bus.publish(accepted())

    assert instance.events == [accepted()]


async def test_listener_that_cannot_be_built_does_not_block_the_others():
    recorder = Recorder(SuggestionAccepted)
    # the container cannot build TypeListener
    bus = EventBus(ListenerRegistry([TypeListener, recorder]), FakeResolver())

    await bus.publish(accepted())

    assert recorder.events == [accepted()]
