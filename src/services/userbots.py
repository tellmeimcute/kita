from typing import Any

from loguru import logger

from core.config import Config
from database.dto import UserBotDTO
from interfaces import BotContextProtocol, UserBotRepositoryProtocol

from .base import BaseService


class UserBotService(BaseService):
    __slots__ = ("repo", "_config")

    def __init__(
        self,
        repo: UserBotRepositoryProtocol,
        bot_context: BotContextProtocol,
        config: Config,
    ):
        super().__init__(bot_context)
        self.repo = repo
        self._config = config

    async def get(self, bot_id: int) -> UserBotDTO | None:
        return await self.repo.get(bot_id)

    async def get_active(self):
        return await self.repo.get_active()

    async def get_by_owner_id(self, owner_id: int):
        return await self.repo.get_by_owner_id(owner_id)

    async def count_by_owner_id(self, owner_id: int) -> int:
        return await self.repo.count_by_owner_id(owner_id)

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ) -> UserBotDTO | None:
        userbot_dto = await self.repo.create(
            token,
            bot_id,
            username,
            owner_id,
            channel_id,
            channel_name,
            max_per_owner=self._config.max_userbots_per_user,
        )
        if userbot_dto is None:
            return None

        logger.info("Create new userbot {}", bot_id)
        return userbot_dto

    async def update(self, bot_id: int, **data: Any):
        await self.repo.update(bot_id, **data)
        logger.info("Update userbot {}", bot_id)

    async def save(self, userbot_dto: UserBotDTO):
        await self.repo.save(userbot_dto)
        logger.info("Update userbot {}", userbot_dto.bot_id)

    async def toggle_active(self, bot_id: int) -> UserBotDTO | None:
        userbot_dto = await self.repo.toggle_active(bot_id)
        logger.info("Toggle userbot {} active: {}", bot_id, userbot_dto and userbot_dto.active)
        return userbot_dto

    async def deactivate(self, bot_id: int) -> UserBotDTO | None:
        userbot_dto = await self.repo.deactivate(bot_id)
        logger.info("Deactivate userbot {}", bot_id)
        return userbot_dto
