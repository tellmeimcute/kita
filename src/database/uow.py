from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis import CacheJournal
from interfaces import (
    BotRegistryProtocol,
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UserProfileRepositoryProtocol,
    UserRepositoryProtocol,
)


class UnitOfWork:
    __slots__ = (
        "_session",
        "_bot_registry",
        "_journal",
        "_in_transaction",
        "users",
        "profiles",
        "suggestions",
        "medias",
    )

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
        journal: CacheJournal,
        user_repo: UserRepositoryProtocol,
        user_profile_repo: UserProfileRepositoryProtocol,
        suggestion_repo: SuggestionRepositoryProtocol,
        media_repo: MediaRepositoryProtocol,
    ):
        self._session = session
        self._bot_registry = bot_registry
        self._journal = journal
        self._in_transaction = False

        self.users = user_repo
        self.profiles = user_profile_repo
        self.suggestions = suggestion_repo
        self.medias = media_repo

    @asynccontextmanager
    async def transaction(self):
        if self._in_transaction:
            # Inside an existing transaction: only the outer block handles commit/rollback.
            yield
            return

        logger.debug("Transaction begin")
        self._in_transaction = True
        self._journal.begin()
        try:
            yield
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            self._journal.discard()
            logger.warning("Transaction rollback")
            raise
        finally:
            self._in_transaction = False
            self._journal.end()

        await self._journal.flush()
        logger.debug("Transaction close")

    async def commit(self):
        await self._session.commit()
        await self._journal.flush()
        logger.debug("Transaction committed")

    async def rollback(self):
        await self._session.rollback()
        self._journal.discard()
        logger.warning("Transaction rollback")
