from typing import Any, Awaitable, Callable, Dict, Union

from aiogram.types import CallbackQuery, Message, TelegramObject

from database.dto import UserDTO
from .base import KitaMiddleware

class AdminMiddleware(KitaMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if not user_dto or not user_dto.is_admin:
            return
        return await handler(event, data)
