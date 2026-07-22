
from contextlib import asynccontextmanager
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession

from interfaces import (
    UserRepositoryProtocol,
    UserProfileRepositoryProtocol,
    SuggestionRepositoryProtocol,
    MediaRepositoryProtocol,
)

logger = getLogger("kita.uow")

class UnitOfWork:

    __slots__ = (
        "_session",
        "users",
        "profiles",
        "suggestions",
        "medias",
    )

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepositoryProtocol,
        user_profile_repo: UserProfileRepositoryProtocol,
        suggestion_repo: SuggestionRepositoryProtocol,
        media_repo: MediaRepositoryProtocol,
    ):
        self._session = session

        self.users = user_repo
        self.profiles = user_profile_repo
        self.suggestions = suggestion_repo
        self.medias = media_repo

    @asynccontextmanager
    async def transaction(self):
        async with self._session.begin():
            logger.debug("Translaction begin")
            yield
        logger.debug("Translaction close")

    async def commit(self):
        await self._session.commit()
        logger.debug("Transaction committed")

    async def rollback(self):
        await self._session.rollback()
        logger.warning("Transaction rollback")
