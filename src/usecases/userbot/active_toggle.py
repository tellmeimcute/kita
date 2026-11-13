from aiogram import Bot
from aiogram.types import User as AiogramUser

from core.userbot_dispatcher import UserbotDispatcherState
from database.dto import UserBotDTO, UserDTO
from events import UserbotActivated, UserbotDeactivated
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    EventBusProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    WebhookServiceProtocol,
)
from utils.userbot_probe import probe_userbot

from .userbot_usecase import UserbotUseCase


class UserbotActiveToggleUseCase(UserbotUseCase):
    __slots__ = ("_events", "_resolver", "_userbot_dispatcher", "_webhook_service")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        webhook_service: WebhookServiceProtocol,
        userbot_dispatcher: UserbotDispatcherState,
        events: EventBusProtocol,
    ):
        super().__init__(bot_context, uow, userbot_service)
        self._resolver = resolver
        self._webhook_service = webhook_service
        self._userbot_dispatcher = userbot_dispatcher
        self._events = events

    async def userbot_deactivate(
        self, bot: Bot, bot_user: AiogramUser | None, userbot: UserBotDTO
    ):
        userbot.active = False
        if bot_user:
            await self._webhook_service.remove_webhook(bot)
        async with self._uow.transaction():
            await self._userbot_service.save(userbot)
            await self._events.publish(
                UserbotDeactivated(
                    bot_id=self.bot.id,
                    userbot_id=userbot.bot_id,
                    owner_id=userbot.owner_id,
                )
            )
        self._resolver.remove(bot.id)

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> UserBotDTO:
        userbot = await super().execute(caller_dto, userbot_id)

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
                await self._events.publish(
                    UserbotActivated(
                        bot_id=self.bot.id,
                        userbot_id=userbot.bot_id,
                        owner_id=userbot.owner_id,
                    )
                )

        return userbot
