from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any
from datetime import datetime

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from core.events import EventBus, NewUserEvent
from core.consts import DISHKA_CONTAINER_KEY

from database.dto import UserDTO
from database.enums import UserRole
from services import UserService, NotifierService

from .base import KitaMiddleware

logger = getLogger("kita.middleware")


class UserMiddleware(KitaMiddleware):
    def __init__(self, config: Config, i18n: I18n):
        self.admin_id = config.admin_id
        self.i18n = i18n

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)

        event_bus = await container.get(EventBus)
        session: AsyncSession = await container.get(AsyncSession)
        user_service: UserService = await container.get(UserService)
        if not session or not event.from_user:
            logger.warning("No user in event. Stop")
            return None
        
        is_new_user = False
        user_tg = event.from_user

        async with session.begin():
            user_dto = await self._resolve_user(user_service, user_tg)
            if not user_dto:
                user_dto = await user_service.create(self.dto_from_aiogram(user_tg))
                is_new_user = True
        
        if is_new_user:
            event_bus.dispatch(NewUserEvent(user_dto=user_dto, container=container))

        data.update(user_dto=user_dto)
        return await handler(event, data)

    async def _resolve_user(
        self,
        user_service: UserService,
        user_tg: AiogramUser,
    ) -> UserDTO | None:
        user_dto = await user_service.get(user_tg.id)
        if not user_dto:
            return None

        user_dto.update_from_data(user_tg)
        if user_dto.is_bot_blocked:
            user_dto.is_bot_blocked = False
        if changed_data := user_dto.prepare_changed_data():
            await user_service.update(user_dto.user_id, **changed_data)
        return user_dto

    def dto_from_aiogram(self, aiogram_user: AiogramUser) -> UserDTO:
        role = UserRole.ADMIN if aiogram_user.id == self.admin_id else UserRole.USER

        language_code = aiogram_user.language_code
        if language_code not in self.i18n.available_locales:
            language_code = self.i18n.default_locale

        return UserDTO(
            user_id=aiogram_user.id,
            username=aiogram_user.username,
            name=aiogram_user.full_name,
            language_code=language_code,
            role=role,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
