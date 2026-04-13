
from logging import getLogger
from typing import Any, Awaitable, Callable, Dict, Union
from dishka import AsyncContainer

from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from core.consts import DISHKA_CONTAINER_KEY
from core.config import Config

from .base import KitaMiddleware

logger = getLogger("kita.middleware")

class SessionMiddleware(KitaMiddleware):
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)

        if container is None:
            logger.error("Container is None. Stop")
            return

        session = await container.get(AsyncSession)
        config = await container.get(Config)

        data.update(session=session, config=config)

        return await handler(event, data)
