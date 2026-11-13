from core.exceptions import UserbotBanned, UserbotNotFoundError
from database.dto import UserBotDTO, UserDTO
from interfaces import BotContextProtocol, UnitOfWorkProtocol, UserBotServiceProtocol
from interfaces.mixins import BotMixin


class UserbotUseCase(BotMixin):
    """
    Base for the use cases that act on a user bot on behalf of its owner.
    """

    __slots__ = ("_userbot_service", "_uow")

    def __init__(
        self,
        bot_context: BotContextProtocol,
        uow: UnitOfWorkProtocol,
        userbot_service: UserBotServiceProtocol,
    ):
        super().__init__(bot_context)
        self._uow = uow
        self._userbot_service = userbot_service

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> UserBotDTO:
        async with self._uow.transaction():
            userbot = await self._userbot_service.get(userbot_id)

        if not userbot or userbot.owner_id != caller_dto.user_id:
            raise UserbotNotFoundError()
        if userbot.banned:
            raise UserbotBanned()

        return userbot
