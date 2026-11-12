from core.exceptions import UserImmuneError
from database.dto import UserBotDTO, UserDTO
from database.enums import UserRole
from events import UserBanned
from interfaces import (
    EventBusProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)


class ChangeRoleUseCase:
    __slots__ = (
        "_user_service",
        "_user_profile_service",
        "_userbot",
        "_events",
    )

    def __init__(
        self,
        user_service: UserServiceProtocol,
        user_profile_service: UserProfileServiceProtocol,
        userbot: UserBotDTO,
        events: EventBusProtocol,
    ):
        self._user_service = user_service
        self._user_profile_service = user_profile_service
        self._userbot = userbot
        self._events = events

    async def execute(
        self,
        target_id: int,
        target_role: UserRole,
        caller: UserDTO,
    ):
        if target_id in {caller.user_id, self._userbot.owner_id}:
            raise UserImmuneError()

        result = await self._user_profile_service.get_or_create(target_id)
        profile_dto = result.dto

        profile_dto.role = target_role
        await self._user_profile_service.save(profile_dto)

        if target_role == UserRole.BANNED:
            await self._user_profile_service.decline_suggestion(profile_dto)
            await self._events.publish(
                UserBanned(
                    bot_id=self._userbot.bot_id,
                    user_id=profile_dto.user_id,
                    admin_id=caller.user_id,
                )
            )

        return profile_dto
