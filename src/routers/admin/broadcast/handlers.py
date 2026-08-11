from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

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
    broadcast_usecase: FromDishka[BroadcastUseCase],
    uow: FromDishka[UnitOfWorkProtocol],
):
    album = manager.middleware_data.get("album")
    if not album:
        album = (message,)

    async with uow.transaction():
        broadcast_data = await broadcast_usecase.prepare(message, album)

    manager.dialog_data.update({"broadcast_data": broadcast_data.model_dump(mode="json")})
    await manager.switch_to(BroadcastMenuSG.broadcast_confirm, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def execute_broadcast(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    broadcast_usecase: FromDishka[BroadcastUseCase],
    userbot: FromDishka[UserBotDTO],
):
    raw_data: dict = manager.dialog_data.get("broadcast_data")
    data = BroadcastData.model_validate(raw_data)

    if not await broadcast_usecase.lock():
        return await callback.answer("Broadcast already started")

    try:
        await broadcast.kiq(
            bot_id=userbot.bot_id,
            caller_id=callback.from_user.id,
            source_chat_id=data.source_chat_id,
            source_message_ids=data.source_message_ids,
            is_forwarded=data.is_forwarded,
        )
        logger.info("Broadcast bot_id {} started", callback.bot.id)
    except Exception:
        await callback.answer("Broadcast failed to start")
        await broadcast_usecase.unlock()
        logger.exception("Broadcast bot_id {} failed to start", callback.bot.id)

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
