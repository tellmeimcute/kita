


from core.config import Config
from core.exceptions import UserImmuneError

from database.dto import UserDTO
from database.enums import UserRole
from interfaces import UserServiceProtocol

class ChangeRoleUseCase:

    __slots__ = (
        "_config",
        "_user_service",
    )

    def __init__(self, config: Config, user_service: UserServiceProtocol):
        self._config = config
        self._user_service = user_service

    async def execute(
        self,
        target_id: int,
        target_role: UserRole,
        caller: UserDTO,
    ):
        if target_id == self._config.admin_id or caller.user_id == target_id:
            raise UserImmuneError()

        target_dto = await self._user_service.get(target_id)
        target_dto.role = target_role
        await self._user_service.save(target_dto)

        if target_role == UserRole.BANNED:
            await self._user_service.decline_suggestion(target_dto)

        # TODO: Dispatch UserBannedEvent with banned_user_dto and admin_dto
        return target_dto