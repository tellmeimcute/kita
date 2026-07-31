from logging import getLogger

from aiogram import F, Router
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter, ExceptionTypeFilter
from aiogram.types import CallbackQuery, ChatMemberUpdated, ErrorEvent
from aiogram_dialog.api.exceptions import UnknownIntent
from dishka import FromDishka

from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserProfileServiceProtocol
from services import UserBotService
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
        event.update.update_id, callback.from_user.id,
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
        ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER),
    )

    router.error.register(
        unknown_intent,
        ExceptionTypeFilter(UnknownIntent), F.update.callback_query.as_("callback")
    )

    return router
