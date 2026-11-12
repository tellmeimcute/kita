from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.exceptions import UnsupportedPayload
from database.dto import UserDTO, UserProfileDTO
from events import SuggestionCreated
from interfaces import EventBusProtocol, SuggestionServiceProtocol, UnitOfWorkProtocol


@inject
async def on_album_received(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    events: FromDishka[EventBusProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    profile_dto: UserProfileDTO = manager.middleware_data.get("profile_dto")
    album = manager.middleware_data.get("album")

    if not album:
        album = (message,)

    try:
        async with uow.transaction():
            suggestion_dto = await suggestion_service.create(
                user_dto,
                album,
                anonymous=profile_dto.prefer_anonymous,
            )
            await events.publish(
                SuggestionCreated(bot_id=message.bot.id, suggestion_id=suggestion_dto.id)
            )
    except UnsupportedPayload:
        manager.dialog_data["something_wrong"] = "suggestion_error_media"
        return

    manager.dialog_data["additional_text_key"] = "suggestion_sent_to_moderation"
