from core.config import Config
from core.exceptions import UserImmuneError
from database.dto import UserDTO, UserBotDTO
from database.enums import UserRole
from interfaces import UserProfileServiceProtocol, UserServiceProtocol


class ChangeRoleUseCase:
    __slots__ = (
        "_config",
        "_user_service",
        "_user_profile_service",
        "_userbot",
    )

    def __init__(
        self,
        config: Config,
        user_service: UserServiceProtocol,
        user_profile_service: UserProfileServiceProtocol,
        userbot: UserBotDTO,
    ):
        self._config = config
        self._user_service = user_service
        self._user_profile_service = user_profile_service
        self._userbot = userbot

    async def execute(
        self,
        target_id: int,
        target_role: UserRole,
        caller: UserDTO,
    ):
        if target_id in {self._config.admin_id, caller.user_id, self._userbot.owner_id}:
            raise UserImmuneError()

        profile_dto = await self._user_profile_service.get_or_create(target_id)

        profile_dto.role = target_role
        await self._user_profile_service.save(profile_dto)

        if target_role == UserRole.BANNED:
            await self._user_profile_service.decline_suggestion(profile_dto)

        # TODO: Dispatch UserBannedEvent with banned_user_dto and admin_dto
        return profile_dto
