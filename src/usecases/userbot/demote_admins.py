from database.dto import UserDTO
from interfaces import (
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
)
from utils.userbot_probe import userbot_action_auth


class UserbotDemoteAdminsUseCase:
    __slots__ = ("_resolver", "_uow", "_userbot_service", "_profile_service")

    def __init__(
        self,
        resolver: BotResolverProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
        profile_service: UserProfileServiceProtocol,
    ):
        self._resolver = resolver
        self._uow = uow
        self._userbot_service = userbot_service
        self._profile_service = profile_service

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> int:
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        userbot_action_auth(caller_dto, userbot)

        bot = self._resolver.get_or_create(userbot_id, userbot.token.get_secret_value())

        async with self._resolver.with_bot(bot), self._uow.transaction():
            return await self._profile_service.demote_admins(userbot.owner_id)
