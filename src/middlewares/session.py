from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class SessionMiddleware(BaseMiddleware):
    """
    ВЫДАЕТ AsyncSession В ХЕНДЛЕРЫ
    """

    __slots__ = (
        "session_maker",
    )

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_maker() as session:
            data.update(session=session)
            return await handler(event, data)
