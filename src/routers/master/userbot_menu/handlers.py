from logging import getLogger
from typing import Any

from aiogram import Router, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramUnauthorizedError, TelegramBadRequest
from aiogram.utils.token import TokenValidationError, extract_bot_id

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Select, Button

from ui.state_groups import UserBotSelectSG
from database.dto import UserDTO
from services import UserBotService, WebhookService
from interfaces import UnitOfWorkProtocol, BotRegistryProtocol, NotifierServiceProtocol

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

        await callback.answer("Userbot active state changed.")
    except TelegramUnauthorizedError:
        async with uow.transaction():
            userbot.active = False
            await userbot_service.save(userbot)

        logger.info("Userbot %s unauthorized: force inactive")
        await callback.answer("Token invalid. Userbot inactive.")
    except Exception as e:
        logger.exception(
            "Something went wrong when user %s trying toggle userbot %s active state:",
            user_dto.user_id, userbot.bot_id,
        )

    await manager.update({"selected_userbot": userbot.model_dump(mode="json")})

        
@inject
async def update_token(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    webhook_service: FromDishka[WebhookService],
    bot_registry: FromDishka[BotRegistryProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
):
    bot_id = int(manager.dialog_data["selected_bot_id"])

    try:
        token = message.text.strip()
        token_bot_id = extract_bot_id(token)
    except (TokenValidationError, AttributeError):
        manager.dialog_data["something_wrong"] = "reg_bot_token_invalid"
        return

    if bot_id != token_bot_id:
        manager.dialog_data["something_wrong"] = "reg_bot_token_from_another_bot"
        return

    async with uow.transaction():
        await userbot_service.update(bot_id, token=token)
        userbot = await userbot_service.get(bot_id)

    if userbot.active:
        bot_registry.remove(bot_id)
        bot = bot_registry.get_or_create(bot_id, token)
        await webhook_service.set_webhook(bot)

    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    await notifier.send_text(user_dto, "userbot_token_updated")

    await manager.switch_to(UserBotSelectSG.moderation)

@inject
async def update_channel(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    bot_registry: FromDishka[BotRegistryProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
):
    if not message.text:
        manager.dialog_data["something_wrong"] = "reg_bot_bad_request"
        return
    
    try:
        provided_channel_id = message.text.strip()
        channel_id = int("-100" + provided_channel_id)
    except ValueError:
        logger.exception("Userbot channel_id to '%s' change failed", provided_channel_id)
        manager.dialog_data["something_wrong"] = "reg_bot_channel_id_should_be_int"
        return

    bot_id = int(manager.dialog_data["selected_bot_id"])

    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)

    bot: Bot = bot_registry.get_or_create(bot_id, userbot.token.get_secret_value())

    try:
        channel = await bot.get_chat(channel_id)
        channel_member = await bot.get_chat_member(channel_id, bot.id)
    except TelegramBadRequest as e:
        logger.exception("Userbot channel_id change failed: %s", e.message)
        manager.dialog_data["something_wrong"] = "reg_bot_bad_request"
        return
    
    if channel_member.status != ChatMemberStatus.ADMINISTRATOR or not channel_member.can_post_messages:
        manager.dialog_data["something_wrong"] = "reg_bot_permission_error"
        return

    async with uow.transaction():
        userbot.channel_id = channel.id
        userbot.channel_name = channel.full_name
        await userbot_service.save(userbot)

    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    await notifier.send_text(user_dto, "userbot_channel_updated")

    await manager.switch_to(UserBotSelectSG.moderation)
