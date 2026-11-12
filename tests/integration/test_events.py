from dishka import AsyncContainer

from events import SuggestionAccepted
from interfaces import EventBusProtocol, UnitOfWorkProtocol

from .scaffold import BOT_ID, EventRecorder


async def test_events_are_dispatched_only_after_commit(
    request_container: AsyncContainer,
    event_recorder: EventRecorder,
):
    events: EventBusProtocol = await request_container.get(EventBusProtocol)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        await events.publish(SuggestionAccepted(bot_id=BOT_ID, suggestion_id=1))
        assert event_recorder.events == []

    assert event_recorder.events == [SuggestionAccepted(bot_id=BOT_ID, suggestion_id=1)]


async def test_events_are_dropped_when_transaction_rolls_back(
    request_container: AsyncContainer,
    event_recorder: EventRecorder,
):
    events: EventBusProtocol = await request_container.get(EventBusProtocol)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        await events.publish(SuggestionAccepted(bot_id=BOT_ID, suggestion_id=1))
        await uow.rollback()

    assert event_recorder.events == []


async def test_event_outside_transaction_is_dispatched_immediately(
    request_container: AsyncContainer,
    event_recorder: EventRecorder,
):
    events: EventBusProtocol = await request_container.get(EventBusProtocol)

    await events.publish(SuggestionAccepted(bot_id=BOT_ID, suggestion_id=1))

    assert event_recorder.events == [SuggestionAccepted(bot_id=BOT_ID, suggestion_id=1)]
