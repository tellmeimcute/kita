

from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Union
from dishka import AsyncContainer

from aiogram.types import CallbackQuery, Message, TelegramObject, User as AiogramUser
from aiogram.utils.i18n import I18n
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import SQLUserNotFoundError
from database.dto import UserDTO
from database.roles import UserRole
from services.user import UserService
from core.consts import DISHKA_CONTAINER_KEY

from core.config import Config

from .base import KitaMiddleware

logger = getLogger("kita.middleware")

class UserMiddleware(KitaMiddleware):

    def __init__(self, config: Config, i18n: I18n):
        self.admin_id = config.ADMIN_ID
        self.i18n = i18n

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")

        if not session or not event.from_user:
            logger.warning("No user in event. Stop")
            return
        
        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        user_service: UserService = await container.get(UserService)

        user_tg = event.from_user

        async with session.begin():
            try:
                user_dto = await user_service.get(user_tg.id)
                user_dto.update_from_data(user_tg)
                if changed_data := user_dto.prepare_changed_data():
                    await user_service.update_from_data(user_dto, changed_data)
            except SQLUserNotFoundError:
                prep_user_dto = self.dto_from_aiogram(user_tg)
                user_dto = await user_service.create(prep_user_dto)

        data.update(user_dto=user_dto, user_service=user_service)
        return await handler(event, data)

    def dto_from_aiogram(self, aiogram_user: AiogramUser) -> UserDTO:
        role = UserRole.ADMIN if aiogram_user.id == self.admin_id else UserRole.USER

        language_code = aiogram_user.language_code
        if language_code not in self.i18n.available_locales:
            language_code = self.i18n.default_locale

        prep_user_dto = UserDTO(
            user_id=aiogram_user.id,
            username=aiogram_user.username,
            name=aiogram_user.full_name,
            language_code=language_code,
            role=role,
            is_bot_blocked=False,
        )

        return prep_user_dto