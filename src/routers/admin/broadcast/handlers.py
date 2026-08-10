from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.schemas.broadcast import BroadcastData
from database.dto import UserBotDTO
from interfaces import UnitOfWorkProtocol
from task_queue.tasks import broadcast
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
    userbot: FromDishka[UserBotDTO],
):
    raw_data: dict = manager.dialog_data.get("broadcast_data")
    data = BroadcastData.model_validate(raw_data)

    await broadcast.kiq(
        bot_id=userbot.bot_id,
        source_chat_id=data.source_chat_id,
        source_message_ids=data.source_message_ids,
        is_forwarded=data.is_forwarded,
    )

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
