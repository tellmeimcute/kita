from loguru import logger

from core.cryptographer import Cryptographer
from core.exceptions import (
    BadRequestError,
    ChannelNotFoundError,
    UserbotAlreadyExistsError,
)
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserBotServiceProtocol
from interfaces.mixins import BotMixin
from utils.userbot_probe import probe_userbot, validate_channel_id


class UserBotRegisterUseCase(BotMixin):
    __slots__ = ("_uow", "_userbot_service", "_crypto")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        crypto: Cryptographer,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._userbot_service = userbot_service
        self._crypto = crypto

    async def execute(self, raw_token: str | None, text_id: str | None, owner_id: int):
        if not raw_token or not text_id:
            raise BadRequestError()

        token = self._crypto.decrypt(raw_token)

        channel_id = validate_channel_id(text_id)
        if not channel_id:
            logger.info("Userbot registration failed: provided channel_id is not valid")
            raise ChannelNotFoundError()

        async with self._bot_registry.temp_bot(token) as tmp_bot:
            probe = await probe_userbot(tmp_bot, channel_id)

        if not probe.ok:
            raise probe.error

        async with self._uow.transaction():
            if await self._userbot_service.get(probe.bot_info.id):
                raise UserbotAlreadyExistsError()

            await self._userbot_service.create(
                token=token,
                bot_id=probe.bot_info.id,
                username=probe.bot_info.username,
                owner_id=owner_id,
                channel_id=probe.channel.id,
                channel_name=probe.channel.full_name,
            )

        self._bot_registry.remove(probe.bot_info.id)
        self._bot_registry.get_or_create(probe.bot_info.id, token)

        return probe.bot_info
