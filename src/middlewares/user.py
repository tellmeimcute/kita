

from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Union
from dishka import AsyncContainer

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from services.user import UserService
from core.exceptions import SQLUserNotFoundError
from helpers.consts import DISHKA_CONTAINER_KEY

logger = getLogger("kita.middleware")

class UserMiddleware(BaseMiddleware):

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
                user_dto = await user_service.create(user_tg)

        data.update(user_dto=user_dto, user_service=user_service)
        return await handler(event, data)
