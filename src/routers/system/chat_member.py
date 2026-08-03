from logging import getLogger

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import (
    IS_ADMIN,
    LEAVE_TRANSITION,
    ChatMemberUpdatedFilter,
    ExceptionTypeFilter,
)
from aiogram.types import CallbackQuery, ChatMemberUpdated, ErrorEvent
from aiogram.utils.i18n import I18n
from aiogram.utils.token import extract_bot_id
from aiogram_dialog.api.exceptions import UnknownIntent
from dishka import FromDishka

from core.config import Config
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from interfaces import (
    BotRegistryProtocol,
    NotifierServiceProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)
from services import UserBotService, WebhookService
from ui.senders.payload import TextSender

logger = getLogger("kita.errors")


async def on_user_block_bot(
    event: ChatMemberUpdated,
    uow: FromDishka[UnitOfWorkProtocol],
    user_profile_service: FromDishka[UserProfileServiceProtocol],
):
    user_id = event.from_user.id
    async with uow.transaction():
        await user_profile_service.update(user_id, is_bot_blocked=True)

    logger.info("UserID %s blocked the bot.", user_id)


async def on_userbot_demoted(
    event: ChatMemberUpdated,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    userbot_service: FromDishka[UserBotService],
    bot_registry: FromDishka[BotRegistryProtocol],
    webhook_service: FromDishka[WebhookService],
    notifier: FromDishka[NotifierServiceProtocol],
    config: FromDishka[Config],
    i18n: FromDishka[I18n],
    tl: FromDishka[Translator],
):
    new = event.new_chat_member

    if new.can_post_messages:
        return

    registrar_token = config.tg_token.get_secret_value()
    registrar_bot_id = extract_bot_id(registrar_token)
    registrar_bot = bot_registry.get_or_create(registrar_bot_id, registrar_token)

    bot = bot_registry.get_current()
    async with uow.transaction():
        await userbot_service.update(bot.id, active=False)
        userbot = await userbot_service.get(bot.id)
        owner_dto = await user_service.get(userbot.owner_id)

    await webhook_service.remove_webhook(bot)
    bot_registry.remove(bot.id)

    with i18n.context(), i18n.use_locale(owner_dto.language_code):
        notifier.assign_bot(registrar_bot)
        await notifier.send_text(
            owner_dto,
            i18n_key="your_bot_deactivated",
            i18n_kwargs={
                "bot_id": bot.id,
                "detail": tl.translate("reg_bot_permission_error"),
                "bot_username": userbot.username,
            },
        )

    logger.info(
        "Bot %s permission in channel %s has been revoked, deactivate userbot",
        bot.id,
        event.chat.title,
    )


async def unknown_intent(
    event: ErrorEvent,
    callback: CallbackQuery,
    translator: FromDishka[Translator],
):
    await callback.answer()

    payload = MessagePayload(i18n_key="warning_unknown_intent")
    strategy = TextSender(
        bot=callback.bot,
        target_id=callback.from_user.id,
        payload=payload,
        translator=translator,
    )

    await strategy.send()

    logger.info(
        "Unknown intent exception on update %s. Send warning to %s userid",
        event.update.update_id,
        callback.from_user.id,
    )


async def userbot_token_invalid(
    event: ErrorEvent,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    bot_registry: FromDishka[BotRegistryProtocol],
):
    bot = bot_registry.get_current()

    async with uow.transaction():
        await userbot_service.update(bot.id, active=False)

    bot_registry.remove(bot.id)

    logger.info("Token invalid for bot %s, set userbot inactive", bot.id)


def get_error_router():
    router = Router(name="kita_errors")

    router.error.register(
        userbot_token_invalid,
        ExceptionTypeFilter(TelegramUnauthorizedError),
    )

    router.my_chat_member.register(
        on_user_block_bot,
        ChatMemberUpdatedFilter(LEAVE_TRANSITION),
        F.chat.type == ChatType.PRIVATE,
    )

    router.my_chat_member.register(
        on_userbot_demoted,
        ChatMemberUpdatedFilter(IS_ADMIN),
        F.chat.type == ChatType.CHANNEL,
    )

    router.error.register(
        unknown_intent, ExceptionTypeFilter(UnknownIntent), F.update.callback_query.as_("callback")
    )

    return router
