from logging import getLogger

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramUnauthorizedError, TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.token import TokenValidationError, extract_bot_id

from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.config import Config
from database.dto import UserDTO
from interfaces import BotRegistryProtocol, NotifierServiceProtocol, UnitOfWorkProtocol
from services import UserBotService, WebhookService
from ui.state_groups import RegistrarMenuSG, UserBotRegisterSG

router = Router(name="registrar")

logger = getLogger("kita.master_reg_userbot")


@inject
async def start_registration(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    config: FromDishka[Config],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    async with uow.transaction():
        userbots = await userbot_service.get_by_owner_id(user_dto.user_id)

    if len(userbots) >= config.max_userbots_per_user:
        return await callback.answer("Userbot limit exceeded!")
    
    await manager.start(UserBotRegisterSG.wait_token)

@inject
async def bot_token_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    notifier: FromDishka[NotifierServiceProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    try:
        token = message.text.strip()
        bot_id = extract_bot_id(token)
    except TokenValidationError:
        manager.dialog_data["something_wrong"] = "reg_bot_token_invalid"
        return
    
    async with uow.transaction():
        if await userbot_service.get(bot_id):
            await notifier.send_text(user_dto, "reg_bot_alredy_exist")
            return await manager.start(RegistrarMenuSG.menu)

    manager.dialog_data["new_userbot_token"] = token
    manager.dialog_data["new_userbot_bot_id"] = bot_id

    await manager.next(ShowMode.DELETE_AND_SEND)
    
@inject
async def channel_id_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    notifier: FromDishka[NotifierServiceProtocol],
    webhook_service: FromDishka[WebhookService],
    bot_registry: FromDishka[BotRegistryProtocol],
):
    if not message.text:
        manager.dialog_data["something_wrong"] = "reg_bot_bad_request"
        return

    try:
        provided_channel_id = message.text.strip()
        channel_id = int("-100" + provided_channel_id)
    except ValueError:
        logger.exception("Userbot registration failed. Trying channel_id '%s'", provided_channel_id)
        manager.dialog_data["something_wrong"] = "reg_bot_channel_id_should_be_int"
        return

    token = manager.dialog_data.get("new_userbot_token")
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    try:
        async with Bot(token=token, **bot_registry.bot_settings) as tmp_bot:
            bot_info = await tmp_bot.get_me()
            channel = await tmp_bot.get_chat(channel_id)
            channel_member = await tmp_bot.get_chat_member(channel_id, bot_info.id)
    except TelegramUnauthorizedError:
        logger.info("Userbot registration failed: invalid token")
        manager.dialog_data["something_wrong"] = "reg_bot_token_invalid"
        await manager.switch_to(UserBotRegisterSG.wait_token)
        return
    except TelegramBadRequest as e:
        logger.exception("Userbot registration failed: %s", e.message)
        manager.dialog_data["something_wrong"] = "reg_bot_bad_request"
        return

    if channel_member.status != ChatMemberStatus.ADMINISTRATOR or not channel_member.can_post_messages:
        manager.dialog_data["something_wrong"] = "reg_bot_permission_error"
        return

    async with uow.transaction():
        await userbot_service.create(
            token=token,
            bot_id=bot_info.id,
            username=bot_info.username,
            owner_id=message.from_user.id,
            channel_id=channel.id,
            channel_name=channel.full_name,
        )
        
    bot_registry.remove(bot_info.id)
    async with Bot(token=token, **bot_registry.bot_settings) as tmp_bot:
        await webhook_service.set_webhook(tmp_bot)

    await notifier.send_text(user_dto, "reg_bot_userbot_registered")

    await manager.start(
        RegistrarMenuSG.menu,
        show_mode=ShowMode.DELETE_AND_SEND,
    )


@router.message(CommandStart())
async def registrar_start_menu(message: Message, state: FSMContext, dialog_manager: DialogManager):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await dialog_manager.start(
        RegistrarMenuSG.menu,
        show_mode=ShowMode.DELETE_AND_SEND,
    )
