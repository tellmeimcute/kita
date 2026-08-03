from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from pydantic import ValidationError

from core.events import CopyMessagesToUserEvent, EventBus
from core.exceptions import UserImmuneError
from core.i18n_translator import Translator
from core.schemas import IDCommand
from database.dto import UserDTO
from database.enums import UserRole
from interfaces import (
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)
from ui.state_groups import ModerationMenuSG
from usecases.change_role import ChangeRoleUseCase


@inject
async def select_user(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    user_profile_service: FromDishka[UserProfileServiceProtocol],
):
    try:
        id_command = IDCommand(target_id=message.text)
        async with uow.transaction():
            target_dto = await user_service.get(id_command.target_id)
            target_profile = await user_profile_service.get(id_command.target_id)
    except ValidationError:
        target_dto = None
        target_profile = None

    if not target_dto or not target_profile:
        manager.dialog_data["user_not_found"] = True
        return

    manager.dialog_data.update(
        {
            "user_not_found": False,
            "target_dto": target_dto.model_dump(mode="json"),
            "target_dto_i18n": target_dto.to_i18n_kwargs(),
            "target_profile": target_profile.model_dump(mode="json") if target_profile else None,
            "target_profile_i18n": target_profile.to_i18n_kwargs() if target_profile else None,
        }
    )
    await manager.switch_to(ModerationMenuSG.user_moderation, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def user_change_role(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    translator: FromDishka[Translator],
    uow: FromDishka[UnitOfWorkProtocol],
    change_role: FromDishka[ChangeRoleUseCase],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    target_dto_raw = manager.dialog_data.get("target_dto")
    target_dto = UserDTO.model_validate(target_dto_raw)

    if button.widget_id == "ban":
        target_role = UserRole.BANNED
    elif button.widget_id == "change_to_user":
        target_role = UserRole.USER
    elif button.widget_id == "promote_admin":
        target_role = UserRole.ADMIN

    try:
        async with uow.transaction():
            new_profile_dto = await change_role.execute(
                target_dto.user_id,
                target_role,
                caller=user_dto,
            )

        await callback.answer()
        await manager.update(
            {
                "target_profile": new_profile_dto.model_dump(mode="json"),
            }
        )
    except UserImmuneError:
        error_msg = translator.translate("error_user_immune")
        await callback.answer(error_msg)


@inject
async def message_to_user(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    event_bus: FromDishka[EventBus],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    target_dto_raw = manager.dialog_data.get("target_dto")
    bot: Bot = manager.middleware_data.get("bot")
    target_dto = UserDTO.model_validate(target_dto_raw)

    album: list[Message] | None = manager.middleware_data.get("album")
    if not album:
        album = (message,)

    album_ids = [m.message_id for m in album]
    event_bus.dispatch(
        CopyMessagesToUserEvent(
            user_dto=target_dto,
            caller_dto=user_dto,
            source_chat_id=message.chat.id,
            album_ids=album_ids,
            bot_id=bot.id,
        )
    )

    await manager.switch_to(ModerationMenuSG.user_moderation, show_mode=ShowMode.DELETE_AND_SEND)
