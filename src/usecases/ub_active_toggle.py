from aiogram import Bot
from aiogram.types import User as AiogramUser

from database.dto import UserBotDTO, UserDTO
from interfaces import (
    BotRegistryProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    WebhookServiceProtocol,
)
from interfaces.mixins import BotMixin
from utils.userbot_probe import probe_userbot, userbot_action_auth


class UserbotActiveToggleUseCase(BotMixin):
    __slots__ = ("_uow", "_userbot_service", "_webhook_service")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        webhook_service: WebhookServiceProtocol,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._userbot_service = userbot_service
        self._webhook_service = webhook_service

    async def userbot_deactivate(
        self, bot: Bot, bot_user: AiogramUser | None, userbot: UserBotDTO
    ):
        userbot.active = False
        if bot_user:
            await self._webhook_service.remove_webhook(bot)
        async with self._uow.transaction():
            await self._userbot_service.save(userbot)
        self._bot_registry.remove(bot.id)

    async def execute(self, caller_dto: UserDTO, userbot_id: int):
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        token = userbot.token.get_secret_value()
        bot = self._bot_registry.get_or_create(userbot_id, token)

        probe = await probe_userbot(bot, userbot.channel_id)
        if not probe.ok:
            await self.userbot_deactivate(bot, probe.bot_info, userbot)
            raise probe.error

        userbot.active = not userbot.active

        if not userbot.active:
            await self.userbot_deactivate(bot, probe.bot_info, userbot)
        if userbot.active:
            await self._webhook_service.set_webhook(bot)
            async with self._uow.transaction():
                await self._userbot_service.save(userbot)

        return userbot
