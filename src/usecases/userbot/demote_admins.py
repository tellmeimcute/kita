from database.dto import UserDTO
from interfaces import (
    BotContextProtocol,
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
)

from .userbot_usecase import UserbotUseCase


class UserbotDemoteAdminsUseCase(UserbotUseCase):
    __slots__ = ("_profile_service", "_resolver")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        profile_service: UserProfileServiceProtocol,
    ):
        super().__init__(bot_context, uow, userbot_service)
        self._resolver = resolver
        self._profile_service = profile_service

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> int:
        userbot = await super().execute(caller_dto, userbot_id)

        bot = self._resolver.get_or_create(userbot_id, userbot.token.get_secret_value())

        async with self._resolver.with_bot(bot), self._uow.transaction():
            return await self._profile_service.demote_admins()
