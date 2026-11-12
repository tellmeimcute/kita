from dataclasses import dataclass

from events import Event, EventBus, EventListener, SuggestionAccepted


@dataclass(frozen=True, slots=True)
class OtherEvent(Event):
    payload: str


class Recorder(EventListener[Event]):
    def __init__(self, event_type: type[Event]):
        self.event_type = event_type
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class Broken(EventListener[Event]):
    event_type = SuggestionAccepted

    async def handle(self, event: Event) -> None:
        raise RuntimeError("broken listener")


def accepted(suggestion_id: int = 1) -> SuggestionAccepted:
    return SuggestionAccepted(bot_id=100, suggestion_id=suggestion_id)


async def test_publish_reaches_only_the_listener_of_the_event_type():
    suggestion = Recorder(SuggestionAccepted)
    other = Recorder(OtherEvent)
    bus = EventBus([suggestion, other])

    await bus.publish(accepted())

    assert suggestion.events == [accepted()]
    assert other.events == []


async def test_event_goes_to_every_listener_of_the_type():
    first = Recorder(SuggestionAccepted)
    second = Recorder(SuggestionAccepted)
    bus = EventBus([first, second])

    await bus.publish(accepted())

    assert first.events == second.events == [accepted()]


async def test_event_without_listeners_is_ignored():
    bus = EventBus([])

    await bus.publish(accepted())


async def test_publish_inside_transaction_is_deferred_until_flush():
    recorder = Recorder(SuggestionAccepted)
    bus = EventBus([recorder])

    bus.begin()
    await bus.publish(accepted())
    bus.end()

    assert recorder.events == []

    await bus.flush()

    assert recorder.events == [accepted()]


async def test_flush_keeps_the_publish_order():
    recorder = Recorder(SuggestionAccepted)
    bus = EventBus([recorder])

    bus.begin()
    await bus.publish(accepted(1))
    await bus.publish(accepted(2))
    bus.end()
    await bus.flush()

    assert [event.suggestion_id for event in recorder.events] == [1, 2]


async def test_discard_drops_deferred_events():
    recorder = Recorder(SuggestionAccepted)
    bus = EventBus([recorder])

    bus.begin()
    await bus.publish(accepted())
    bus.end()
    bus.discard()

    await bus.flush()

    assert recorder.events == []


async def test_flushed_events_are_not_dispatched_twice():
    recorder = Recorder(SuggestionAccepted)
    bus = EventBus([recorder])

    bus.begin()
    await bus.publish(accepted())
    bus.end()

    await bus.flush()
    await bus.flush()

    assert recorder.events == [accepted()]


async def test_nested_begin_keeps_events_deferred():
    recorder = Recorder(SuggestionAccepted)
    bus = EventBus([recorder])

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
    bus = EventBus([Broken(), recorder])

    await bus.publish(accepted())

    assert recorder.events == [accepted()]


async def test_subscribe_after_creation_is_picked_up():
    bus = EventBus([])
    recorder = Recorder(SuggestionAccepted)

    bus.subscribe(recorder)
    await bus.publish(accepted())

    assert recorder.events == [accepted()]
