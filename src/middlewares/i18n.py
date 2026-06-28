from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any, ClassVar

from aiogram import Router
from aiogram.types import TelegramObject
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from core.consts import DISHKA_CONTAINER_KEY
from database.dto import UserDTO
from services.user import UserService

from .base import KitaMiddleware

logger = getLogger("kita.middleware")


class KitaI18nMiddleware(KitaMiddleware):
    __event__types__: ClassVar[set[str]] = {
        "update",
        "my_chat_member",
        "chat_member",
    }

    def __init__(
        self, i18n: I18n, i18n_key: str | None = "i18n", middleware_key: str = "i18n_middleware"
    ):
        self.i18n = i18n
        self.i18n_key = i18n_key
        self.middleware_key = middleware_key

    async def get_user_dto(self, data: dict[str, Any]):
        user_dto: UserDTO = data.get("user_dto")
        if user_dto:
            return user_dto

        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        session: AsyncSession = await container.get(AsyncSession)
        user_service: UserService = await container.get(UserService)

        aiogram_user: AiogramUser = data.get("event_from_user")

        async with session.begin():
            return await user_service.get(aiogram_user.id)


    async def get_locale(self, data: dict[str, Any]):
        user_dto: UserDTO | None = await self.get_user_dto(data)
        if not user_dto:
            return self.i18n.default_locale

        if user_dto.language_code in self.i18n.available_locales:
            return user_dto.language_code

        return self.i18n.default_locale

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        current_locale = await self.get_locale(data=data)

        if self.i18n_key:
            data[self.i18n_key] = self.i18n
        if self.middleware_key:
            data[self.middleware_key] = self

        logger.debug("Context use locale %s", current_locale)
        with self.i18n.context(), self.i18n.use_locale(current_locale):
            return await handler(event, data)

    def setup(self, router: Router):
        for event_name, observer in router.observers.items():
            if event_name not in self.__event__types__:
                observer.outer_middleware(self)
                logger.debug(
                    "%s registered to event %s on router: %s",
                    self.__class__.__name__, event_name, router.name,
                )
        return self
