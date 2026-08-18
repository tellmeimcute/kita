from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from loguru import logger

from core.consts import DISHKA_CONTAINER_KEY
from database.dto import UserDTO
from interfaces import (
    BotRegistryProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)

from .base import KitaMiddleware


class UserMiddleware(KitaMiddleware):
    def __init__(
        self,
        i18n: I18n,
        bot_registry: BotRegistryProtocol,
    ):
        self.i18n = i18n
        self.bot_registry = bot_registry

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)

        uow = await container.get(UnitOfWorkProtocol)
        user_service = await container.get(UserServiceProtocol)
        user_profile_service = await container.get(UserProfileServiceProtocol)

        if not event.from_user or event.from_user.is_bot:
            return logger.warning("No user in event. Stop")

        user_tg = event.from_user
        async with uow.transaction():
            user_dto = await user_service.get_or_create(self.dto_from_tg(user_tg))
            profile_dto = await user_profile_service.get_or_create(user_tg.id)

            user_dto.update_from_data(user_tg)
            await user_service.save(user_dto)

            if profile_dto.is_bot_blocked:
                profile_dto.is_bot_blocked = False

            await user_profile_service.save(profile_dto)

        data.update(user_dto=user_dto, profile_dto=profile_dto)
        return await handler(event, data)

    def dto_from_tg(self, aiogram_user: AiogramUser) -> UserDTO:
        language_code = aiogram_user.language_code
        if language_code not in self.i18n.available_locales:
            language_code = self.i18n.default_locale

        return UserDTO(
            user_id=aiogram_user.id,
            username=aiogram_user.username,
            name=aiogram_user.full_name,
            language_code=language_code,
        )
