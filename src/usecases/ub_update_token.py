from database.dto import UserDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol
from interfaces.mixins import BotMixin
from services import UserBotService, WebhookService
from utils.userbot_probe import parse_token, probe_token, userbot_action_auth


class UserbotUpdateTokenUseCase(BotMixin):
    __slots__ = ("_uow", "_userbot_service", "_webhook_service")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotService,
        webhook_service: WebhookService,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._userbot_service = userbot_service
        self._webhook_service = webhook_service

    async def execute(self, caller_dto: UserDTO, userbot_id: int, raw_token: str | None) -> None:
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        token = parse_token(raw_token, expected_bot_id=userbot_id)
        await probe_token(self._bot_registry.bot_settings, token)

        async with self._uow.transaction():
            userbot.token = token
            await self._userbot_service.save(userbot)

        if userbot.active:
            self._bot_registry.remove(userbot_id)
            bot = self._bot_registry.get_or_create(userbot_id, token)
            await self._webhook_service.set_webhook(bot)
