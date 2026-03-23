from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as UserAiogram
from sqlalchemy.ext.asyncio import AsyncSession

from services.user import UserService


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
        if not session:
            return await handler(event, data)

        user_tg: UserAiogram = None

        if isinstance(event, (Message, CallbackQuery)):
            user_tg = event.from_user

        if not user_tg:
            return await handler(event, data)

        user_service: UserService = data["user_service"]

        user_dto = await user_service.get(user_tg.id)
        if user_dto:
            await user_service.update(user_dto, user_tg)
        if not user_dto:
            user_dto = await user_service.create(user_tg)

        data["user_dto"] = user_dto
        return await handler(event, data)
