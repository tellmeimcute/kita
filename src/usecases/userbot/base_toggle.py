from aiogram import Bot

from core.userbot_dispatcher import UserbotDispatcherState
from database.dto import UserBotDTO
from events import UserbotActivated, UserbotDeactivated
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    EventBusProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    WebhookServiceProtocol,
)

from .userbot_usecase import UserbotUseCase


class BaseToggle(UserbotUseCase):
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

    def _bot_for(self, userbot: UserBotDTO) -> Bot:
        return self._resolver.get_or_create(userbot.bot_id, userbot.token.get_secret_value())

    async def activate(self, bot: Bot, userbot: UserBotDTO) -> UserBotDTO:
        async with self._uow.transaction():
            activated = await self._userbot_service.activate(userbot.bot_id)

        if activated is None:
            return userbot

        await self._webhook_service.set_webhook(
            bot,
            allowed_updates=self._userbot_dispatcher.allowed_updates,
        )
        await self._events.publish(
            UserbotActivated(
                bot_id=self.bot.id,
                userbot_id=activated.bot_id,
                owner_id=activated.owner_id,
            )
        )

        return activated

    async def deactivate(self, bot: Bot, userbot: UserBotDTO) -> UserBotDTO:
        await self._webhook_service.remove_webhook(bot)

        async with self._uow.transaction():
            deactivated = await self._userbot_service.deactivate(userbot.bot_id)

        self._resolver.remove(userbot.bot_id)

        if deactivated is None:
            return userbot

        await self._events.publish(
            UserbotDeactivated(
                bot_id=self.bot.id,
                userbot_id=deactivated.bot_id,
                owner_id=deactivated.owner_id,
            )
        )

        return deactivated
