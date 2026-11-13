from core.userbot_dispatcher import UserbotDispatcherState
from database.dto import UserDTO
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    WebhookServiceProtocol,
)
from utils.userbot_probe import parse_token, probe_token

from .userbot_usecase import UserbotUseCase


class UserbotUpdateTokenUseCase(UserbotUseCase):
    __slots__ = ("_resolver", "_userbot_dispatcher", "_webhook_service")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        webhook_service: WebhookServiceProtocol,
        userbot_dispatcher: UserbotDispatcherState,
    ):
        super().__init__(bot_context, uow, userbot_service)
        self._resolver = resolver
        self._webhook_service = webhook_service
        self._userbot_dispatcher = userbot_dispatcher

    async def execute(self, caller_dto: UserDTO, userbot_id: int, raw_token: str | None) -> None:
        userbot = await super().execute(caller_dto, userbot_id)

        token = parse_token(raw_token, expected_bot_id=userbot_id)
        async with self._resolver.temp_bot(token) as tmp_bot:
            await probe_token(tmp_bot)

        async with self._uow.transaction():
            userbot.token = token
            await self._userbot_service.save(userbot)

        if userbot.active:
            self._resolver.remove(userbot_id)
            bot = self._resolver.get_or_create(userbot_id, token)
            await self._webhook_service.set_webhook(
                bot, allowed_updates=self._userbot_dispatcher.allowed_updates
            )
