from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from core.exceptions import UserbotBanned, UserbotError, UserbotNotFoundError
from core.i18n_translator import Translator
from database.dto import UserDTO
from interfaces import MessageNotifierProtocol, UnitOfWorkProtocol
from services import UserBotService
from ui.state_groups import UserBotSelectSG
from usecases import (
    UserbotActiveToggleUseCase,
    UserbotDemoteAdminsUseCase,
    UserbotUpdateChannelUseCase,
    UserbotUpdateTokenUseCase,
)
from utils.userbot_probe import userbot_action_auth


@inject
async def on_bot_selected(
    callback: CallbackQuery,
    widget: Select,
    manager: DialogManager,
    item_id: str,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    item_id: int = int(item_id)

    async with uow.transaction():
        userbot = await userbot_service.get(item_id)

    try:
        userbot_action_auth(user_dto, userbot)
    except UserbotError as e:
        return await callback.answer(tl.translate(e.error_key))

    manager.dialog_data.update(selected_bot_id=item_id)
    return await manager.switch_to(UserBotSelectSG.moderation)


@inject
async def userbot_active_toggle(
    callback: CallbackQuery,
    widget: Button,
    manager: DialogManager,
    tl: FromDishka[Translator],
    active_toggle: FromDishka[UserbotActiveToggleUseCase],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    try:
        userbot = await active_toggle.execute(user_dto, bot_id)
    except UserbotError as e:
        return await callback.answer(tl.translate(e.error_key))

    await manager.update({"selected_userbot": userbot.model_dump(mode="json")})


@inject
async def userbot_update_token(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    update_token: FromDishka[UserbotUpdateTokenUseCase],
    notifier: FromDishka[MessageNotifierProtocol],
):
    try:
        await message.delete()
    except Exception:
        logger.exception("Token message delete failed")

    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    try:
        await update_token.execute(user_dto, bot_id, message.text)
    except (UserbotNotFoundError, UserbotBanned) as e:
        return await notifier.send_text(user_dto, e.error_key)
    except UserbotError as e:
        manager.dialog_data["something_wrong"] = e.error_key
        return None

    await notifier.send_text(user_dto, "userbot_token_updated")

    await manager.switch_to(UserBotSelectSG.moderation)


@inject
async def userbot_update_channel(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    update_channel: FromDishka[UserbotUpdateChannelUseCase],
    notifier: FromDishka[MessageNotifierProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    try:
        await update_channel.execute(user_dto, bot_id, message.text)
    except (UserbotNotFoundError, UserbotBanned) as e:
        return await notifier.send_text(user_dto, e.error_key)
    except UserbotError as e:
        manager.dialog_data["something_wrong"] = e.error_key
        return None

    await notifier.send_text(user_dto, "userbot_channel_updated")

    await manager.switch_to(UserBotSelectSG.moderation)


@inject
async def userbot_demote_admins(
    callback: CallbackQuery,
    widget: Button,
    manager: DialogManager,
    demote_admins: FromDishka[UserbotDemoteAdminsUseCase],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    try:
        await demote_admins.execute(user_dto, bot_id)
    except UserbotError as e:
        return await callback.answer(tl.translate(e.error_key))

    await callback.answer(tl.translate("userbot_admins_demoted"))
