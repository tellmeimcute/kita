from typing import Any

from loguru import logger

from database.dto import UserBotDTO
from interfaces import BotRegistryProtocol, UserBotRepositoryProtocol

from .base import BaseService


class UserBotService(BaseService):
    __slots__ = ("repo",)

    def __init__(
        self,
        repo: UserBotRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.repo = repo

    async def get(self, bot_id: int) -> UserBotDTO | None:
        return await self.repo.get(bot_id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_by_owner_id(self, owner_id: int):
        return await self.repo.get_by_owner_id(owner_id)

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        await self.repo.create(token, bot_id, username, owner_id, channel_id, channel_name)
        logger.info("Create new userbot {}", bot_id)

    async def update(self, bot_id: int, **data: Any):
        await self.repo.update(bot_id, **data)
        logger.info("Update userbot {}", bot_id)

    async def save(self, userbot_dto: UserBotDTO):
        await self.repo.save(userbot_dto)
        logger.info("Update userbot {}", userbot_dto.bot_id)
