from loguru import logger

from core.exceptions import ChannelNotFoundError
from database.dto import UserBotDTO, UserDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol
from interfaces.mixins import BotMixin
from services import UserBotService
from utils.userbot_probe import probe_userbot, userbot_action_auth, validate_channel_id


class UserbotUpdateChannelUseCase(BotMixin):
    __slots__ = ("_uow", "_userbot_service")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotService,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._userbot_service = userbot_service

    async def execute(
        self, caller_dto: UserDTO, userbot_id: int, raw_channel: str | None
    ) -> UserBotDTO:
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        channel_id = validate_channel_id(raw_channel)
        if not channel_id:
            logger.warning("Userbot {} channel_id change failed", userbot_id)
            raise ChannelNotFoundError()

        bot = self._bot_registry.get_or_create(userbot_id, userbot.token.get_secret_value())

        probe = await probe_userbot(bot, channel_id)
        if not probe.ok:
            raise probe.error

        async with self._uow.transaction():
            userbot.channel_id = probe.channel.id
            userbot.channel_name = probe.channel.full_name
            await self._userbot_service.save(userbot)

        return userbot
