from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as UserAiogram
from sqlalchemy.ext.asyncio import AsyncSession

from services.user import UserService

from helpers.exceptions import SQLModelNotFoundError

class UserMiddleware(BaseMiddleware):
    """
    ВЫДАЕТ UserDTO В ХЕНДЛЕРЫ
    data["user_dto]
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")

        if not session or not event.from_user:
            return await handler(event, data)
        
        user_tg = event.from_user
        user_service: UserService = data["user_service"]
        
        async with session.begin():
            try:
                user_dto = await user_service.get(user_tg.id)
                await user_service.update_from_data(user_dto, user_tg)
            except SQLModelNotFoundError:
                user_dto = await user_service.create(user_tg)

        data.update(user_dto=user_dto)
        return await handler(event, data)
