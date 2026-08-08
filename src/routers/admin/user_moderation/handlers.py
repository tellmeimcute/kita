from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
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
async def on_user_selected(
    callback: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data.update(selected_user_id=int(item_id))
    return await manager.switch_to(ModerationMenuSG.user_moderation)


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
        manager.dialog_data["something_wrong"] = "user_not_found_wait_next_id"
        return

    manager.dialog_data.update({"selected_user_id": target_dto.user_id})
    await manager.switch_to(ModerationMenuSG.user_moderation, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def user_change_role(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    translator: FromDishka[Translator],
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    change_role: FromDishka[ChangeRoleUseCase],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    user_id = manager.dialog_data["selected_user_id"]
    if not user_id:
        return

    async with uow.transaction():
        target_dto = await user_service.get(int(user_id))

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
                "target_profile_i18n": new_profile_dto.to_i18n_kwargs(),
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
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    user_id = manager.dialog_data["selected_user_id"]
    if not user_id:
        return

    async with uow.transaction():
        target_dto = await user_service.get(int(user_id))

    bot: Bot = manager.middleware_data.get("bot")

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
