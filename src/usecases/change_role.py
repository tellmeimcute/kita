


from core.config import Config
from core.exceptions import UserImmuneError

from database.dto import UserDTO
from database.enums import UserRole

from services import UserService


class ChangeRoleUseCase:

    __slots__ = (
        "_config",
        "_user_service",
    )

    def __init__(
        self,
        config: Config,
        user_service: UserService,
    ):
        self._config = config
        self._user_service = user_service

    def is_immune(self, user_id: int):
        return user_id == self._config.ADMIN_ID

    async def execute(
        self,
        target_id: int,
        target_role: UserRole,
        caller: UserDTO,
    ):
        if self.is_immune(target_id) or caller.user_id == target_id:
            raise UserImmuneError()

        target_dto = await self._user_service.get(target_id)
        target_dto.role = target_role
        await self._user_service.save(target_dto)

        if target_role == UserRole.BANNED:
            await self._user_service.decline_suggestion(target_dto)

        return target_dto