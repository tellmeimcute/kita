from logging import getLogger

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from database.dto import UserBotDTO, UserDTO
from interfaces import BotRegistryProtocol, NotifierServiceProtocol, UnitOfWorkProtocol
from services import UserBotService, WebhookService
from ui.state_groups import UserBotSelectSG
from utils.userbot_checker import UserBotChecker, UserBotCheckResult

logger = getLogger("kita.userbot_moderation")


def action_auth(user_dto: UserDTO, userbot: UserBotDTO | None) -> str | None:
    detail = None

    if not userbot or userbot.owner_id != user_dto.user_id:
        detail = "userbot_not_found"
    elif userbot.banned:
        detail = "userbot_is_banned"

    return detail


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

    if auth_error := action_auth(user_dto, userbot):
        return await callback.answer(tl.translate(auth_error))

    manager.dialog_data.update(selected_bot_id=item_id)
    return await manager.switch_to(UserBotSelectSG.moderation)


@inject
async def userbot_active_toggle(
    callback: CallbackQuery,
    widget: Button,
    manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    webhook_service: FromDishka[WebhookService],
    bot_registry: FromDishka[BotRegistryProtocol],
    tl: FromDishka[Translator],
    checker: FromDishka[UserBotChecker],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)

    if auth_error := action_auth(user_dto, userbot):
        return await callback.answer(tl.translate(auth_error))

    userbot.active = not userbot.active

    bot = bot_registry.get_or_create(bot_id, userbot.token.get_secret_value())

    check_result: UserBotCheckResult = await checker.full_check(bot, userbot.channel_id)
    if not check_result.success:
        await callback.answer(tl.translate(check_result.detail_i18n_key))
        if check_result.bot_info:
            await webhook_service.remove_webhook(bot)
        async with uow.transaction():
            userbot.active = False
            await userbot_service.save(userbot)
        bot_registry.remove(bot.id)
        return None

    try:
        if not userbot.active:
            await webhook_service.remove_webhook(bot)
        if userbot.active:
            await webhook_service.set_webhook(bot)
        async with uow.transaction():
            await userbot_service.save(userbot)
    except Exception:
        logger.exception(
            "Something went wrong when user %s trying toggle userbot %s active state:",
            user_dto.user_id,
            userbot.bot_id,
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
    checker: FromDishka[UserBotChecker],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)

    if auth_error := action_auth(user_dto, userbot):
        return await notifier.send_text(user_dto, auth_error)

    check_result = await checker.check_token(bot_id, message.text, bot_registry.bot_settings)
    if not check_result.success:
        manager.dialog_data["something_wrong"] = check_result.detail_i18n_key
        return None

    async with uow.transaction():
        userbot.token = check_result.token
        await userbot_service.save(userbot)

    if userbot.active:
        bot_registry.remove(bot_id)
        bot = bot_registry.get_or_create(bot_id, check_result.token)
        await webhook_service.set_webhook(bot)

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
    checker: FromDishka[UserBotChecker],
):
    user_dto: UserDTO = manager.middleware_data.get("user_dto")
    bot_id = int(manager.dialog_data["selected_bot_id"])

    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)

    if auth_error := action_auth(user_dto, userbot):
        return await notifier.send_text(user_dto, auth_error)

    try:
        channel_id = checker.get_channel_id(message.text)
    except (ValueError, AttributeError):
        logger.exception("Userbot %s channel_id change failed", bot_id)
        manager.dialog_data["something_wrong"] = "reg_bot_channel_id_error"
        return None

    bot: Bot = bot_registry.get_or_create(bot_id, userbot.token.get_secret_value())

    check_result: UserBotCheckResult = await checker.full_check(bot, channel_id)
    if not check_result.success:
        manager.dialog_data["something_wrong"] = check_result.detail_i18n_key
        return None

    async with uow.transaction():
        userbot.channel_id = check_result.channel.id
        userbot.channel_name = check_result.channel.full_name
        await userbot_service.save(userbot)

    await notifier.send_text(user_dto, "userbot_channel_updated")

    await manager.switch_to(UserBotSelectSG.moderation)
