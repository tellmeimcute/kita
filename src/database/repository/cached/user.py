from typing import Any

from database.dto import Created, UserDTO
from database.redis import CacheJournal, KitaKeyBuilder, UserRedis
from interfaces import BotContextProtocol

from ..user import UserRepository
from .base import CachedRepository


class CachedUserRepository(CachedRepository):
    REDIS_KEY_PART = "user"

    __slots__ = ("repo",)

    def __init__(
        self,
        bot_context: BotContextProtocol,
        redis: UserRedis,
        journal: CacheJournal,
        repo: UserRepository,
    ):
        key_builder = KitaKeyBuilder(with_bot_id=False)
        super().__init__(bot_context, redis, journal, key_builder)
        self.repo = repo

    async def get_by_id(self, user_id: int) -> UserDTO | None:
        return await self._cache_or_load(
            self._get_key(user_id),
            lambda: self.repo.get_by_id(user_id),
        )

    async def get_or_create(self, prep_user_dto: UserDTO) -> Created[UserDTO]:
        key = self._get_key(prep_user_dto.user_id)

        if (cached := await self._redis.get(key)) is not None:
            return Created(cached, created=False)

        result = await self.repo.get_or_create(prep_user_dto)
        await self._journal.invalidate(self._redis, key)
        return result

    async def update(self, user_id: int, **data: Any):
        result = await self.repo.update(user_id, **data)
        await self._journal.invalidate(self._redis, self._get_key(user_id))
        return result

    async def create(self, dto: UserDTO):
        result = await self.repo.create(dto)
        await self._journal.invalidate(self._redis, self._get_key(dto.user_id))
        return result

    async def count(self) -> int:
        return await self.repo.count()
