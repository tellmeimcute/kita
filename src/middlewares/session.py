from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


class SessionMiddleware(BaseMiddleware):
    """
    ВЫДАЕТ AsyncSession В ХЕНДЛЕРЫ(data)
    data["session"]
    """

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_maker() as session:
            data["session"] = session
            return await handler(event, data)
