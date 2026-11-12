from unittest.mock import AsyncMock

from database.redis import CacheJournal
from database.uow import UnitOfWork
from events import EventBus, EventListener, SuggestionAccepted

EVENT = SuggestionAccepted(bot_id=100, suggestion_id=1)


class Probe(EventListener[SuggestionAccepted]):
    """Does what a listener is allowed to do once it runs outside the transaction."""

    event_type = SuggestionAccepted

    def __init__(self, uow: UnitOfWork, journal: CacheJournal, redis: AsyncMock):
        self._uow = uow
        self._journal = journal
        self._redis = redis
        self.journal_was_active: bool | None = None

    async def handle(self, event: SuggestionAccepted) -> None:
        self.journal_was_active = self._journal.active

        async with self._uow.transaction():
            pass

        await self._journal.set(self._redis, "key", {"event": event.suggestion_id})


async def test_listener_runs_outside_the_transaction():
    session, journal, redis, bus = AsyncMock(), CacheJournal(), AsyncMock(), EventBus([])
    uow = UnitOfWork(
        session=session,
        bot_context=None,
        journal=journal,
        events=bus,
        user_repo=None,
        user_profile_repo=None,
        suggestion_repo=None,
        media_repo=None,
    )
    probe = Probe(uow, journal, redis)
    bus.subscribe(probe)

    async with uow.transaction():
        await bus.publish(EVENT)

    # the listener's own transaction is real: one commit for the block, one for it
    assert session.commit.await_count == 2
    # the cache journal is closed already, so the write goes straight to redis
    assert probe.journal_was_active is False
    redis.set_cache.assert_awaited_once_with("key", {"event": 1})
