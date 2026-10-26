from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from core.config import Config
from core.cryptographer import Cryptographer
from core.exceptions import UserbotAlreadyExistsError, UserbotError
from core.i18n_translator import Translator
from database.dto import UserDTO
from interfaces import (
    BotRegistryProtocol,
    MessageNotifierProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
)
from task_queue.tasks import new_userbot
from ui.state_groups import RegistrarMenuSG, UserBotRegisterSG
from usecases import UserBotRegisterUseCase
from utils.userbot_probe import parse_token, probe_token


@inject
async def start_registration(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotServiceProtocol],
    config: FromDishka[Config],
    tl: FromDishka[Translator],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    async with uow.transaction():
        userbots = await userbot_service.get_by_owner_id(user_dto.user_id)

    if len(userbots) >= config.max_userbots_per_user:
        return await callback.answer(tl.translate("reg_bot_limit_exceeded"))

    await manager.start(UserBotRegisterSG.wait_token)


@inject
async def bot_token_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    crypto: FromDishka[Cryptographer],
    bot_registry: FromDishka[BotRegistryProtocol],
):
    try:
        await message.delete()
    except TelegramBadRequest as e:
        logger.warning("Token message delete failed: {}", e.message)

    try:
        token = parse_token(message.text)
        await probe_token(bot_registry.tmp_bot_settings, token)

        manager.dialog_data["new_userbot_token"] = crypto.encrypt(token)
        await manager.next(ShowMode.DELETE_AND_SEND)
    except UserbotError as e:
        manager.dialog_data["something_wrong"] = e.error_key


@inject
async def channel_id_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    notifier: FromDishka[MessageNotifierProtocol],
    register: FromDishka[UserBotRegisterUseCase],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    raw_token = manager.dialog_data.get("new_userbot_token")

    try:
        bot_info = await register.execute(
            raw_token,
            message.text,
            owner_id=user_dto.user_id,
        )

        await notifier.send_text(user_dto, "reg_bot_userbot_registered")
        await manager.start(
            RegistrarMenuSG.menu,
            show_mode=ShowMode.DELETE_AND_SEND,
        )

        await new_userbot.kiq(
            bot_id=message.bot.id,
            userbot_id=bot_info.id,
            owner_id=user_dto.user_id,
        )
    except UserbotAlreadyExistsError as e:
        await notifier.send_text(user_dto, e.error_key)
        await manager.start(RegistrarMenuSG.menu)
    except UserbotError as e:
        manager.dialog_data["something_wrong"] = e.error_key
