
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from core.exceptions import UnsupportedPayload
from core.schemas.message_payload import MessagePayload

from database.dto import UserDTO
from services.user import UserService
from services.notifier import NotifierService
from services.suggestion import SuggestionService

from ui.state_groups import SuggestionSG
from ui.suggestion_utils import SuggestionUtils


@inject
async def on_album_received(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    session: FromDishka[AsyncSession],
    suggestion_service: FromDishka[SuggestionService],
    notifier: FromDishka[NotifierService],
    user_service: FromDishka[UserService],
    suggestion_utils: FromDishka[SuggestionUtils],
):
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

    admins = await user_service.get_admins()
    i18n_kwargs = suggestion_utils.get_i18n_kwargs(suggestion_dto)
    payload = MessagePayload(i18n_key="suggestion_notify_admin_new", i18n_kwargs=i18n_kwargs)
    asyncio.create_task(notifier.notify_many(admins, payload))
