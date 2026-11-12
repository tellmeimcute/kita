from typing import ClassVar

from core.exceptions import UserImmuneError
from database.dto import UserBotDTO, UserDTO, UserProfileDTO
from database.enums import UserRole
from interfaces import UnitOfWorkProtocol, UserProfileServiceProtocol


class RoleChangeUseCase:
    """Base for the use cases that put one fixed role on a profile."""

    __slots__ = ("_profiles", "_uow", "_userbot")

    TARGET_ROLE: ClassVar[UserRole]

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        user_profile_service: UserProfileServiceProtocol,
        userbot: UserBotDTO,
    ):
        self._uow = uow
        self._profiles = user_profile_service
        self._userbot = userbot

    async def execute(self, target_id: int, caller: UserDTO) -> UserProfileDTO:
        async with self._uow.transaction():
            return await self._apply(target_id, caller)

    async def _apply(self, target_id: int, caller: UserDTO) -> UserProfileDTO:
        if target_id in {caller.user_id, self._userbot.owner_id}:
            raise UserImmuneError()

        profile_dto = (await self._profiles.get_or_create(target_id)).dto
        profile_dto.role = self.TARGET_ROLE
        await self._profiles.save(profile_dto)

        return profile_dto
