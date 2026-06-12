

import asyncio

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config, RuntimeConfig
from core.exceptions import SQLUserNotFoundError, UserImmuneError
from core.i18n_translator import Translator
from core.schemas import IDCommand
from core.schemas.data import MassMessageData
from core.schemas.message_payload import MessagePayload
from database.dto import UserDTO
from database.roles import UserRole
from services import NotifierService, UserService
from ui.state_groups import AdminMenuSG
from usecases.broadcast import BroadcastUseCase
from usecases.change_role import ChangeRoleUseCase

router = Router(name="admin_menu")


@inject
async def select_user(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    session: FromDishka[AsyncSession],
    user_service: FromDishka[UserService]
):
    id_command = IDCommand(target_id=message.text)

    try:
        async with session.begin():
            target_dto = await user_service.get(id_command.target_id)
    except SQLUserNotFoundError:
        await manager.switch_to(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
        return
    
    manager.dialog_data.update({"target_dto": target_dto.model_dump()})

    await manager.switch_to(AdminMenuSG.user_moderation, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def user_change_role(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    session: FromDishka[AsyncSession],
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
        async with session.begin():
            new_target_dto = await change_role.execute(
                target_dto.user_id,
                target_role,
                caller=user_dto,
            )

        await callback.answer("Success")
        await manager.update(
            {"target_dto": new_target_dto.model_dump()}
        )
    except UserImmuneError:
        await callback.answer("UserImmuneError")


@inject
async def post_banner(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    translator: FromDishka[Translator],
    notifier: FromDishka[NotifierService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig]
):
    builder = InlineKeyboardBuilder()
    builder.button(text="Предложка", url=runtime_config.bot_url)

    payload = MessagePayload(i18n_key="channel_banner", reply_markup=builder.as_markup())
    strategy = notifier.send_strategy_factory(config.CHANNEL_ID, payload)
    await notifier.send(strategy)

    text = translator.get_translated_text("channel_banner_sent")
    await callback.answer(text)


@inject
async def prepare_broadcast(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    broadcast: FromDishka[BroadcastUseCase],
    session: FromDishka[AsyncSession],
):
    album = manager.middleware_data.get("album")
    if not album:
        album = (message,)

    async with session.begin():
        broadcast_data = await broadcast.prepare(message, album)

    manager.dialog_data.update({"broadcast_data": broadcast_data.model_dump()})

    await manager.switch_to(AdminMenuSG.broadcast_confirm, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def execute_broadcast(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    broadcast: FromDishka[BroadcastUseCase],
    notifier: FromDishka[NotifierService],
    translator: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    raw_data: dict = manager.dialog_data.get("broadcast_data")
    broadcast_data = MassMessageData.model_validate(raw_data)

    i18n_kwargs = broadcast_data.model_dump()
    i18n_kwargs["status"] = translator.get_translated_text(
        i18n_key="completed" if broadcast_data.status else "in_process"
    )
    payload = MessagePayload(i18n_key="broadcast_status_text", i18n_kwargs=i18n_kwargs)
    status_message = await notifier.notify_user(user_dto, payload)
    asyncio.create_task(broadcast.execute(broadcast_data, status_message))

    await manager.switch_to(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)



