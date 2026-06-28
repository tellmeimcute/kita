

import asyncio

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from core.schemas.broadcast import BroadcastData
from core.schemas.message_payload import MessagePayload

from interfaces import UnitOfWorkProtocol
from database.dto import UserDTO

from services import NotifierService
from ui.state_groups import AdminMenuSG, BroadcastMenuSG

from usecases.broadcast import BroadcastUseCase


@inject
async def prepare_broadcast(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    broadcast: FromDishka[BroadcastUseCase],
    uow: FromDishka[UnitOfWorkProtocol],
):
    album = manager.middleware_data.get("album")
    if not album:
        album = (message,)

    async with uow.transaction():
        broadcast_data = await broadcast.prepare(message, album)

    manager.dialog_data.update({"broadcast_data": broadcast_data.model_dump(mode="json")})

    await manager.switch_to(BroadcastMenuSG.broadcast_confirm, show_mode=ShowMode.DELETE_AND_SEND)


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
    broadcast_data = BroadcastData.model_validate(raw_data)

    i18n_kwargs = broadcast_data.model_dump()
    i18n_kwargs["status"] = translator.translate(
        i18n_key="completed" if broadcast_data.is_completed else "in_process"
    )
    payload = MessagePayload(i18n_key="broadcast_status_text", i18n_kwargs=i18n_kwargs)
    status_message = await notifier.notify_user(user_dto, payload)
    asyncio.create_task(broadcast.execute(broadcast_data, status_message))

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
