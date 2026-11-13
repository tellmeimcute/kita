from loguru import logger

from core.exceptions import ChannelNotFoundError
from database.dto import UserBotDTO, UserDTO
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
)
from utils.userbot_probe import probe_userbot, validate_channel_id

from .userbot_usecase import UserbotUseCase


class UserbotUpdateChannelUseCase(UserbotUseCase):
    __slots__ = ("_resolver",)

    def __init__(
        self,
        bot_context: BotContextProtocol,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
    ):
        super().__init__(bot_context, uow, userbot_service)
        self._resolver = resolver

    async def execute(
        self, caller_dto: UserDTO, userbot_id: int, raw_channel: str | None
    ) -> UserBotDTO:
        userbot = await super().execute(caller_dto, userbot_id)

        channel_id = validate_channel_id(raw_channel)
        if not channel_id:
            logger.warning("Userbot {} channel_id change failed", userbot_id)
            raise ChannelNotFoundError()

        bot = self._resolver.get_or_create(userbot_id, userbot.token.get_secret_value())

        probe = await probe_userbot(bot, channel_id)
        if not probe.ok:
            raise probe.error

        async with self._uow.transaction():
            userbot.channel_id = probe.channel.id
            userbot.channel_name = probe.channel.full_name
            await self._userbot_service.save(userbot)

        return userbot
