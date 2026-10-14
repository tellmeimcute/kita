from database.dto import UserDTO
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserProfileServiceProtocol
from interfaces.mixins import BotMixin
from services import UserBotService
from utils.userbot_probe import userbot_action_auth


class UserbotDemoteAdminsUseCase(BotMixin):
    __slots__ = ("_uow", "_userbot_service", "_profile_service")

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotService,
        profile_service: UserProfileServiceProtocol,
    ):
        super().__init__(bot_registry)
        self._uow = uow
        self._userbot_service = userbot_service
        self._profile_service = profile_service

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> int:
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        bot = self._bot_registry.get_or_create(userbot_id, userbot.token.get_secret_value())

        async with self._bot_registry.with_bot(bot), self._uow.transaction():
            return await self._profile_service.demote_admins(userbot.owner_id)
