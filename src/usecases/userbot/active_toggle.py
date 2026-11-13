from aiogram import Bot

from core.exceptions import UserbotBanned, UserbotError
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

    async def deactivate(self, bot: Bot, userbot: UserBotDTO):
        await self._webhook_service.remove_webhook(bot)

        async with self._uow.transaction():
            if await self._userbot_service.deactivate(userbot.bot_id):
                await self._events.publish(
                    UserbotDeactivated(
                        bot_id=self.bot.id,
                        userbot_id=userbot.bot_id,
                        owner_id=userbot.owner_id,
                    )
                )

        self._resolver.remove(bot.id)

    async def activate(self, bot: Bot, userbot: UserBotDTO):
        await self._webhook_service.set_webhook(
            bot,
            allowed_updates=self._userbot_dispatcher.allowed_updates,
        )

        await self._events.publish(
            UserbotActivated(
                bot_id=self.bot.id,
                userbot_id=userbot.bot_id,
                owner_id=userbot.owner_id,
            )
        )

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> UserBotDTO:
        userbot = await super().execute(caller_dto, userbot_id)

        token = userbot.token.get_secret_value()
        bot = self._resolver.get_or_create(userbot_id, token)

        try:
            await probe_userbot(bot, userbot.channel_id)
        except UserbotError:
            await self.deactivate(bot, userbot)
            raise

        async with self._uow.transaction():
            toggled = await self._userbot_service.toggle_active(userbot_id)

        if toggled is None:
            raise UserbotBanned()

        if not toggled.active:
            await self.deactivate(bot, toggled)
        else:
            await self.activate(bot, toggled)

        return toggled
