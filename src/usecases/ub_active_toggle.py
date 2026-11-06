from aiogram import Bot
from aiogram.types import User as AiogramUser

from core.userbot_dispatcher import UserbotDispatcherState
from database.dto import UserBotDTO, UserDTO
from interfaces import (
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    WebhookServiceProtocol,
)
from utils.userbot_probe import probe_userbot, userbot_action_auth


class UserbotActiveToggleUseCase:
    __slots__ = (
        "_resolver",
        "_uow",
        "_userbot_service",
        "_webhook_service",
        "_userbot_dispatcher",
    )

    def __init__(
        self,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        webhook_service: WebhookServiceProtocol,
        userbot_dispatcher: UserbotDispatcherState,
    ):
        self._resolver = resolver
        self._uow = uow
        self._userbot_service = userbot_service
        self._webhook_service = webhook_service
        self._userbot_dispatcher = userbot_dispatcher

    async def userbot_deactivate(
        self, bot: Bot, bot_user: AiogramUser | None, userbot: UserBotDTO
    ):
        userbot.active = False
        if bot_user:
            await self._webhook_service.remove_webhook(bot)
        async with self._uow.transaction():
            await self._userbot_service.save(userbot)
        self._resolver.remove(bot.id)

    async def execute(self, caller_dto: UserDTO, userbot_id: int):
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        token = userbot.token.get_secret_value()
        bot = self._resolver.get_or_create(userbot_id, token)

        probe = await probe_userbot(bot, userbot.channel_id)
        if not probe.ok:
            await self.userbot_deactivate(bot, probe.bot_info, userbot)
            raise probe.error

        userbot.active = not userbot.active

        if not userbot.active:
            await self.userbot_deactivate(bot, probe.bot_info, userbot)
        if userbot.active:
            await self._webhook_service.set_webhook(
                bot, allowed_updates=self._userbot_dispatcher.allowed_updates
            )
            async with self._uow.transaction():
                await self._userbot_service.save(userbot)

        return userbot
