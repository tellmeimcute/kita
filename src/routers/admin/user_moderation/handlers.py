from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from pydantic import ValidationError

from core.exceptions import UserImmuneError
from core.i18n_translator import Translator
from core.schemas import IDCommand
from database.dto import UserDTO
from interfaces import (
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)
from ui.state_groups import ModerationMenuSG
from usecases import (
    BanUserUseCase,
    DemoteUserUseCase,
    MessageUserUseCase,
    PromoteUserUseCase,
)
from usecases.role_changers import RoleChangeUseCase


@inject
async def on_user_selected(
    callback: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data.update(selected_user_id=int(item_id))
    return await manager.switch_to(ModerationMenuSG.user_moderation)


async def set_user_filter(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    **kwargs,
):
    manager.dialog_data["user_filter"] = button.widget_id.removeprefix("filter_")
    await manager.update()


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
async def _apply_role_change(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    usecase: RoleChangeUseCase,
    translator: FromDishka[Translator],
) -> None:
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    target_id = manager.dialog_data.get("selected_user_id")
    if not target_id:
        return

    try:
        new_profile_dto = await usecase.execute(int(target_id), caller=user_dto)
    except UserImmuneError:
        error_msg = translator.translate("error_user_immune")
        await callback.answer(error_msg)
        return

    await callback.answer()
    await manager.update(
        {
            "target_profile": new_profile_dto.model_dump(mode="json"),
            "target_profile_i18n": new_profile_dto.to_i18n_kwargs(),
        }
    )


@inject
async def user_promote(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    usecase: FromDishka[PromoteUserUseCase],
):
    await _apply_role_change(callback, button, manager, usecase=usecase)


@inject
async def user_demote(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    usecase: FromDishka[DemoteUserUseCase],
):
    await _apply_role_change(callback, button, manager, usecase=usecase)


@inject
async def user_ban(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    usecase: FromDishka[BanUserUseCase],
):
    await _apply_role_change(callback, button, manager, usecase=usecase)


@inject
async def message_to_user(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    message_user_usecase: FromDishka[MessageUserUseCase],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    user_id = manager.dialog_data["selected_user_id"]
    if not user_id:
        return

    await manager.switch_to(ModerationMenuSG.user_moderation, show_mode=ShowMode.DELETE_AND_SEND)

    async with uow.transaction():
        target_dto = await user_service.get(int(user_id))

    album: list[Message] | None = manager.middleware_data.get("album")
    if not album:
        album = (message,)

    album_ids = [m.message_id for m in album]

    await message_user_usecase.execute(
        target_dto,
        user_dto,
        album_ids,
        message.chat.id,
    )
