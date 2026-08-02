from logging import getLogger

from aiogram import Router
from aiogram.types import CallbackQuery

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select
from ui.state_groups import UserBotSelectSG

router = Router(name="registrar")

logger = getLogger("kita.master_reg_userbot")


async def on_bot_selected(
    callback: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
):
    manager.dialog_data["selected_bot_id"] = item_id
    return await manager.switch_to(UserBotSelectSG.moderation)
