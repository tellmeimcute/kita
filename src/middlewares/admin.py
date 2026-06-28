from typing import Any, Awaitable, Callable, Dict, Union

from dishka import AsyncContainer
from aiogram.types import CallbackQuery, Message, TelegramObject

from core.consts import DISHKA_CONTAINER_KEY
from core.schemas.message_payload import MessagePayload
from core.i18n_translator import Translator
from database.dto import UserDTO
from services import NotifierService
from ui.senders.payload import TextSender
from .base import KitaMiddleware

class AdminMiddleware(KitaMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        user_dto: UserDTO = data.get("user_dto")
        if user_dto and user_dto.is_admin:
            return await handler(event, data)
        
        if isinstance(event, CallbackQuery):
            await event.answer()

        container: AsyncContainer = data.get(DISHKA_CONTAINER_KEY)
        notifier: NotifierService = await container.get(NotifierService)
        translator: Translator = await container.get(Translator)

        payload = MessagePayload(i18n_key="warning_not_enough_permission")
        strategy = TextSender(
            bot=event.bot,
            target_id=event.from_user.id,
            payload=payload,
            translator=translator,
        )
        await notifier.send(strategy)