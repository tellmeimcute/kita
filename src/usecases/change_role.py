


from core.config import Config
from core.exceptions import UserImmuneError

from database.dto import UserDTO, UserProfileDTO
from database.enums import UserRole
from interfaces import UserServiceProtocol, UserProfileServiceProtocol

class ChangeRoleUseCase:

    __slots__ = (
        "_config",
        "_user_service",
        "_user_profile_service",
    )

    def __init__(
        self,
        config: Config,
        user_service: UserServiceProtocol,
        user_profile_service: UserProfileServiceProtocol
    ):
        self._config = config
        self._user_service = user_service
        self._user_profile_service = user_profile_service

    async def execute(
        self,
        target_id: int,
        target_role: UserRole,
        caller: UserDTO,
    ):
        if target_id == self._config.admin_id or caller.user_id == target_id:
            raise UserImmuneError()

        profile_dto = await self._user_profile_service.get_or_create(target_id)

        profile_dto.role = target_role
        await self._user_profile_service.save(profile_dto)

        if target_role == UserRole.BANNED:
            await self._user_profile_service.decline_suggestion(profile_dto)

        # TODO: Dispatch UserBannedEvent with banned_user_dto and admin_dto
        return profile_dto
