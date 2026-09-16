from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from loguru import logger

from core.consts import DISHKA_CONTAINER_KEY
from interfaces import (
    BotRegistryProtocol,
    UnitOfWorkProtocol,
)
from usecases import UserRegisterOrUpdateUseCase

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
        if not event.from_user or event.from_user.is_bot:
            return logger.warning("No user in event. Stop")

        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        register_or_update = await container.get(UserRegisterOrUpdateUseCase)

        uow = await container.get(UnitOfWorkProtocol)

        async with uow.transaction():
            result = await register_or_update.execute(event.from_user)

        data.update(user_dto=result.user, profile_dto=result.profile)
        return await handler(event, data)
