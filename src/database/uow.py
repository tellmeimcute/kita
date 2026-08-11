from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

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
        "users",
        "profiles",
        "suggestions",
        "medias",
    )

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
        user_repo: UserRepositoryProtocol,
        user_profile_repo: UserProfileRepositoryProtocol,
        suggestion_repo: SuggestionRepositoryProtocol,
        media_repo: MediaRepositoryProtocol,
    ):
        self._session = session
        self._bot_registry = bot_registry

        self.users = user_repo
        self.profiles = user_profile_repo
        self.suggestions = suggestion_repo
        self.medias = media_repo

    @asynccontextmanager
    async def transaction(self):
        logger.debug("Transaction begin")
        try:
            yield
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.warning("Transaction rollback")
            raise
        logger.debug("Transaction close")

    async def commit(self):
        await self._session.commit()
        logger.debug("Transaction committed")

    async def rollback(self):
        await self._session.rollback()
        logger.warning("Transaction rollback")
