from dataclasses import dataclass

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.html import quote
from core.i18n_translator import Translator
from database.dto import UserBotDTO, UserDTO
from interfaces import UnitOfWorkProtocol, UserBotServiceProtocol

STATUS_BANNED_EMOJI = "🚫"
STATUS_INACTIVE_EMOJI = "🔴"
STATUS_ACTIVE_EMOJI = "🟢"


@dataclass(frozen=True)
class UserbotListItem:
    bot_id: int
    username: str
    label: str


def status_emoji(userbot: UserBotDTO) -> str:
    if userbot.banned:
        return STATUS_BANNED_EMOJI
    if not userbot.active:
        return STATUS_INACTIVE_EMOJI
    return STATUS_ACTIVE_EMOJI


def userbot_label(userbot: UserBotDTO) -> str:
    return f"{status_emoji(userbot)} @{userbot.username}"


def empty_selected(translator: Translator) -> dict:
    return {
        "selected_userbot": None,
        "ub_username": "",
        "ub_bot_id": "",
        "ub_channel": translator.translate("userbot_no_channel"),
        "ub_status": "",
        "ub_ban": "",
    }


@inject
async def owned_userbots(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotServiceProtocol],
    **kwargs,
):
    user_dto: UserDTO = dialog_manager.middleware_data.get("user_dto")
    async with uow.transaction():
        userbots = await userbot_service.get_by_owner_id(user_dto.user_id)

    items = [
        UserbotListItem(
            bot_id=userbot.bot_id,
            username=userbot.username,
            label=userbot_label(userbot),
        )
        for userbot in userbots
    ]

    return {"userbots": items}


@inject
async def get_selected_userbot(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotServiceProtocol],
    translator: FromDishka[Translator],
    **kwargs,
):
    bot_id = dialog_manager.dialog_data.get("selected_bot_id")
    if not bot_id:
        return empty_selected(translator)

    async with uow.transaction():
        userbot = await userbot_service.get(int(bot_id))

    if not userbot:
        return empty_selected(translator)

    channel = (
        quote(userbot.channel_name)
        if userbot.channel_name
        else translator.translate("userbot_no_channel")
    )
    status = translator.translate(
        "userbot_status_active" if userbot.active else "userbot_status_inactive"
    )
    ban = translator.translate("userbot_ban_active" if userbot.banned else "userbot_ban_clear")

    return {
        "selected_userbot": userbot,
        "ub_username": quote(userbot.username),
        "ub_bot_id": userbot.bot_id,
        "ub_channel": channel,
        "ub_status": status,
        "ub_ban": ban,
    }
