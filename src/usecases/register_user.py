from dataclasses import dataclass

from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n

from database.dto import UserDTO, UserProfileDTO
from interfaces import (
    BotRegistryProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)
from interfaces.mixins import BotMixin


@dataclass
class RegisterResult:
    user: UserDTO
    profile: UserProfileDTO


class UserRegisterOrUpdateUseCase(BotMixin):
    __slots__ = (
        "_i18n",
        "_user_service",
        "_profile_service",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        i18n: I18n,
        user_service: UserServiceProtocol,
        profile_service: UserProfileServiceProtocol,
    ):
        super().__init__(bot_registry)
        self._i18n = i18n
        self._user_service = user_service
        self._profile_service = profile_service

    async def execute(self, from_user: AiogramUser):
        user_dto = await self._user_service.get_or_create(self.dto_from_tg(from_user))
        profile_dto = await self._profile_service.get_or_create(from_user.id)
        await self.update_user_data(from_user, user_dto, profile_dto)

        return RegisterResult(user_dto, profile_dto)

    async def update_user_data(
        self,
        from_user: AiogramUser,
        user_dto: UserDTO,
        profile_dto: UserProfileDTO,
    ):
        user_dto.update_from_data(from_user)

        if changed_data := user_dto.prepare_changed_data():
            await self._user_service.update(user_dto.user_id, **changed_data)

        if profile_dto.is_bot_blocked:
            profile_dto.is_bot_blocked = False

        if changed_data := profile_dto.prepare_changed_data():
            await self._profile_service.update(profile_dto.user_id, **changed_data)

    def dto_from_tg(self, from_user: AiogramUser) -> UserDTO:
        language_code = from_user.language_code
        if language_code not in self._i18n.available_locales:
            language_code = self._i18n.default_locale

        return UserDTO(
            user_id=from_user.id,
            username=from_user.username,
            name=from_user.full_name,
            language_code=language_code,
        )
