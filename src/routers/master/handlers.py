from aiogram import Bot, Router
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message
from aiogram.utils.token import extract_bot_id, TokenValidationError

from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from ui.state_groups import RegistrarMenuSG
from database.dto import UserDTO
from services import UserBotService, WebhookService
from interfaces import UnitOfWorkProtocol, NotifierServiceProtocol


router = Router(name="registrar_start")

@inject
async def bot_token_handler(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
):
    token = message.text.strip()
    
    try:
        bot_id = extract_bot_id(token)
    except TokenValidationError:
        manager.dialog_data["something_wrong"] = "reg_bot_token_invalid"
        return await manager.show(show_mode=ShowMode.EDIT)
    
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
):
    if not message.text:
        manager.dialog_data["something_wrong"] = "reg_bot_exception"
        return await manager.show(show_mode=ShowMode.DELETE_AND_SEND)

    channel_id = "-100" + message.text.strip()
    token = manager.dialog_data.get("new_userbot_token")
    user_dto: UserDTO = manager.middleware_data.get("user_dto")

    try:
        async with Bot(token=token) as tmp_bot:
            bot_info = await tmp_bot.get_me()
            channel = await tmp_bot.get_chat(channel_id)
            channel_member = await tmp_bot.get_chat_member(channel_id, bot_info.id)
    except TelegramUnauthorizedError:
        manager.dialog_data["something_wrong"] = "reg_bot_token_invalid"
        return await manager.show(show_mode=ShowMode.DELETE_AND_SEND)
    except:
        manager.dialog_data["something_wrong"] = "reg_bot_exception"
        return await manager.show(show_mode=ShowMode.DELETE_AND_SEND)

    if channel_member.status != ChatMemberStatus.ADMINISTRATOR or not channel_member.can_post_messages:
        manager.dialog_data["something_wrong"] = "reg_bot_channel_not_enough_permission"
        return await manager.show(show_mode=ShowMode.DELETE_AND_SEND)

    async with uow.transaction():
        userbot = await userbot_service.get(bot_info.id)

        if userbot and userbot.token == token:
            await notifier.send_text(user_dto, "reg_bot_alredy_exist")
            return await manager.start(
                RegistrarMenuSG.menu,
                show_mode=ShowMode.DELETE_AND_SEND,
            )
        
        if not userbot:
            await userbot_service.create(
                token=token,
                bot_id=bot_info.id,
                username=bot_info.username,
                owner_id=message.from_user.id,
                channel_id=channel.id,
                channel_name=channel.full_name,
            )
        elif userbot:
            await userbot_service.update(
                bot_info.id,
                token=token,
                username=bot_info.username,
                owner_id=message.from_user.id,
                channel_id=channel.id,
                channel_name=channel.full_name,
            )

    async with Bot(token=token) as tmp_bot:
        await webhook_service.set_webhook(tmp_bot)

    await notifier.send_text(user_dto, "reg_bot_userbot_registered")

    await manager.start(
        RegistrarMenuSG.menu,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )


@router.message(CommandStart())
async def start_registration(message: Message, state: FSMContext, dialog_manager: DialogManager):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await dialog_manager.start(
        RegistrarMenuSG.menu,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.DELETE_AND_SEND,
    )
