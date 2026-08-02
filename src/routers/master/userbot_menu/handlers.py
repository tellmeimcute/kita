from logging import getLogger
from typing import Any
from aiogram import Router
from aiogram.types import CallbackQuery

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select, Button
from ui.state_groups import UserBotSelectSG

from database.dto import UserDTO
from services import UserBotService, WebhookService
from interfaces import UnitOfWorkProtocol, BotRegistryProtocol

router = Router(name="registrar")

logger = getLogger("kita.userbot_moderation")


async def on_bot_selected(
    callback: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data["selected_bot_id"] = item_id
    return await manager.switch_to(UserBotSelectSG.moderation)


@inject
async def userbot_set_toggle(
    callback: CallbackQuery,
    widget: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    webhook_service: FromDishka[WebhookService],
    bot_registry: FromDishka[BotRegistryProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)
        userbot.active = not userbot.active
        await userbot_service.save(userbot)

    bot = bot_registry.get_or_create(
        bot_id, userbot.token.get_secret_value()
    )

    try:
        if not userbot.active:
            await webhook_service.remove_webhook(bot)
        if userbot.active:
            await webhook_service.set_webhook(bot)
    except Exception as e:
        logger.exception(
            "Something went wrong when user %s trying toggle userbot %s active state:",
            user_dto.user_id, userbot.bot_id,
        )

    await manager.update({"selected_userbot": userbot})
        
        

    
    