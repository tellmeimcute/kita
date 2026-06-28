

from pydantic import ValidationError

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.exceptions import UserImmuneError
from core.schemas import IDCommand
from core.i18n_translator import Translator

from interfaces import UnitOfWorkProtocol, UserServiceProtocol
from database.dto import UserDTO
from database.enums import UserRole
from ui.state_groups import ModerationMenuSG

from usecases.change_role import ChangeRoleUseCase


@inject
async def select_user(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
):
    try:
        id_command = IDCommand(target_id=message.text)
        async with uow.transaction():
            target_dto = await user_service.get(id_command.target_id)
    except ValidationError:
        target_dto = None

    if not target_dto:
        return await manager.switch_to(
            ModerationMenuSG.user_select_again, show_mode=ShowMode.DELETE_AND_SEND
        )

    manager.dialog_data.update({
        "target_dto": target_dto.model_dump(mode="json"),
        "target_dto_i18n": target_dto.to_i18n_kwargs(),
    })
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
            new_target_dto = await change_role.execute(
                target_dto.user_id,
                target_role,
                caller=user_dto,
            )

        await callback.answer()
        await manager.update({
            "target_dto": new_target_dto.model_dump(mode="json"),
            "target_dto_i18n": new_target_dto.to_i18n_kwargs(),
        })
    except UserImmuneError:
        error_msg = translator.translate("error_user_immune")
        await callback.answer(error_msg)
