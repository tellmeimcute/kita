from typing import Any

from loguru import logger

from database.dto import UserProfileDTO
from interfaces import BotRegistryProtocol, UserProfileRepositoryProtocol

from .base import BaseService


class UserProfileService(BaseService):
    __slots__ = ("repo",)

    def __init__(
        self,
        repo: UserProfileRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.repo = repo

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        return await self.repo.get_or_create(user_id)

    async def get(self, user_id: int) -> UserProfileDTO | None:
        return await self.repo.get_by_id(user_id)

    async def get_many(self, limit: int = 10, offset: int = 0, order_desc: bool = False):
        return await self.repo.get_many(limit, offset, order_desc)

    async def create(self, user_id: int) -> UserProfileDTO:
        return await self.repo.create(user_id)

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        logger.info("Update user profile {} for bot {}", user_id, self.bot.id)

    async def save(self, profile_dto: UserProfileDTO):
        changed = profile_dto.prepare_changed_data()
        if not changed:
            return

        await self.repo.update(profile_dto.user_id, **changed)
        logger.info("Update user profile {} for bot {}", profile_dto.user_id, self.bot.id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_admins(self):
        return await self.repo.get_admins()

    async def decline_suggestion(self, profile_dto: UserProfileDTO):
        await self.repo.decline_all_suggestions(profile_dto.user_id)
