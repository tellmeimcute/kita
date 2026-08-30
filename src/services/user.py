from typing import Any

from loguru import logger

from database.dto import UserDTO
from interfaces import BotRegistryProtocol, UserRepositoryProtocol

from .base import BaseService


class UserService(BaseService):
    __slots__ = ("repo",)

    def __init__(
        self,
        repo: UserRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.repo = repo

    async def create(self, prep_user_dto: UserDTO):
        user_dto = await self.repo.create(prep_user_dto)

        logger.info("Created new user {}", user_dto.user_id)
        logger.debug("New user data: {}", user_dto)

        return user_dto

    async def get(self, user_id: int) -> UserDTO | None:
        return await self.repo.get_by_id(user_id)

    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO:
        return await self.repo.get_or_create(prep_user_dto)

    async def update(self, user_id: int, **data: Any):
        await self.repo.update(user_id, **data)
        logger.info("Update database info for user {}", user_id)

    async def save(self, user_dto: UserDTO):
        changed = user_dto.prepare_changed_data()
        if not changed:
            return

        await self.repo.update(user_dto.user_id, **changed)
        logger.info("Update database info for user {}", user_dto.user_id)
