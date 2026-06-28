
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from core.exceptions import UnsupportedPayload
from core.consts import DISHKA_CONTAINER_KEY
from core.events import EventBus, NewSuggestionEvent

from database.dto import UserDTO
from services.suggestion import SuggestionService

from ui.state_groups import SuggestionSG


@inject
async def on_album_received(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    session: FromDishka[AsyncSession],
    suggestion_service: FromDishka[SuggestionService],
    event_bus: FromDishka[EventBus],
):
    container = manager.middleware_data.get(DISHKA_CONTAINER_KEY)
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    album = manager.middleware_data.get("album")

    if not album:
        album = (message,)

    try:
        async with session.begin():
            suggestion_dto = await suggestion_service.create(user_dto, album)
    except UnsupportedPayload:
        await session.rollback()
        return await manager.switch_to(SuggestionSG.media_error, show_mode=ShowMode.DELETE_AND_SEND)

    await manager.switch_to(SuggestionSG.on_moderation)

    await event_bus.dispatch(NewSuggestionEvent(suggestion_dto=suggestion_dto))