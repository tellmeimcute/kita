from logging import getLogger

from aiogram import Bot, Router
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
from services.userbot_checker import UserBotChecker, UserBotCheckResult

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
    bot_registry: FromDishka[BotRegistryProtocol],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    checker = UserBotChecker()
    check_result = await checker.check_token(
        None, message.text, bot_registry.bot_settings
    )

    if not check_result.success:
        manager.dialog_data["something_wrong"] = check_result.detail_i18n_key
        return

    async with uow.transaction():
        if await userbot_service.get(check_result.bot_id):
            await notifier.send_text(user_dto, "reg_bot_alredy_exist")
            return await manager.start(RegistrarMenuSG.menu)

    manager.dialog_data["new_userbot_token"] = check_result.token
    manager.dialog_data["new_userbot_bot_id"] = check_result.bot_id

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

    checker = UserBotChecker()
    async with Bot(token=token, **bot_registry.bot_settings) as tmp_bot:
        check_result: UserBotCheckResult = await checker.full_check(tmp_bot, channel_id)

    if not check_result.success:
        manager.dialog_data["something_wrong"] = check_result.detail_i18n_key
        return

    async with uow.transaction():
        await userbot_service.create(
            token=token,
            bot_id=check_result.bot_info.id,
            username=check_result.bot_info.username,
            owner_id=message.from_user.id,
            channel_id=check_result.channel.id,
            channel_name=check_result.channel.full_name,
        )
        
    bot_registry.remove(check_result.bot_info.id)
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
