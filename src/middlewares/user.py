from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any
from datetime import datetime

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer

from core.config import Config
from core.events import EventBus, NewUserEvent
from core.consts import DISHKA_CONTAINER_KEY

from database.dto import UserDTO, UserProfileDTO
from database.enums import UserRole
from interfaces import (
    UnitOfWorkProtocol,
    UserServiceProtocol,
    UserProfileServiceProtocol,
    BotRegistryProtocol
)

from .base import KitaMiddleware

logger = getLogger("kita.middleware")


class UserMiddleware(KitaMiddleware):
    def __init__(
        self,
        config: Config,
        i18n: I18n,
        bot_registry: BotRegistryProtocol,
    ):
        self.admin_id = config.admin_id
        self.i18n = i18n
        self.bot_registry = bot_registry

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)

        event_bus = await container.get(EventBus)
        uow = await container.get(UnitOfWorkProtocol)
        user_service = await container.get(UserServiceProtocol)
        user_profile_service = await container.get(UserProfileServiceProtocol)

        if not event.from_user or event.from_user.is_bot:
            return logger.warning("No user in event. Stop")

        user_tg = event.from_user
        async with uow.transaction():
            user_dto = await self._resolve_user(user_service, user_profile_service, user_tg)
            profile_dto = await self._resolve_profile(event_bus, user_profile_service, user_dto, user_tg)

        data.update(user_dto=user_dto, profile_dto=profile_dto)
        return await handler(event, data)

    async def _resolve_profile(
        self,
        event_bus: EventBus,
        user_profile_service: UserProfileServiceProtocol,
        user_dto: UserDTO,
        user_tg: AiogramUser,
    ) -> UserProfileDTO:
        profile_dto = await user_profile_service.get(user_tg.id)
        if profile_dto:
            return profile_dto
        
        profile_dto = await user_profile_service.create(user_tg.id)
        if profile_dto.user_id == self.admin_id:
            profile_dto.role = UserRole.ADMIN
            await user_profile_service.save(profile_dto)

        bot = self.bot_registry.get_current()
        event_bus.dispatch(NewUserEvent(user_dto=user_dto, bot_id=bot.id))
        return profile_dto

    async def _resolve_user(
        self,
        user_service: UserServiceProtocol,
        user_profile_service: UserProfileServiceProtocol,
        user_tg: AiogramUser,
    ) -> UserDTO:
        user_dto = await user_service.get(user_tg.id)
        if user_dto:
            return await self._update_user_data(
                user_service, user_profile_service, user_dto, user_tg
            )
        
        user_dto = await user_service.create(self.dto_from_aiogram(user_tg))
        return user_dto

    async def _update_user_data(
        self,
        user_service: UserServiceProtocol,
        user_profile_service: UserProfileServiceProtocol,
        user_dto: UserDTO,
        user_tg: AiogramUser,
    ):
        user_dto.update_from_data(user_tg)
        if changed_data := user_dto.prepare_changed_data():
            await user_service.update(user_dto.user_id, **changed_data)

        profile_dto = await user_profile_service.get(user_dto.user_id)
        if profile_dto and profile_dto.is_bot_blocked:
            profile_dto.is_bot_blocked = False
            await user_profile_service.save(profile_dto)

        return user_dto

    def dto_from_aiogram(self, aiogram_user: AiogramUser) -> UserDTO:
        language_code = aiogram_user.language_code
        if language_code not in self.i18n.available_locales:
            language_code = self.i18n.default_locale

        return UserDTO(
            user_id=aiogram_user.id,
            username=aiogram_user.username,
            name=aiogram_user.full_name,
            language_code=language_code,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
