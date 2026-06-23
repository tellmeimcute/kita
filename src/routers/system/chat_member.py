from logging import getLogger

from aiogram import Router, F
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter, ExceptionTypeFilter
from aiogram.types import ChatMemberUpdated, CallbackQuery, ErrorEvent

from aiogram_dialog.api.exceptions import UnknownIntent

from dishka import FromDishka
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.message_payload import MessagePayload
from core.i18n_translator import Translator
from ui.senders.payload import TextSender

from services import UserService, NotifierService


router = Router(name="chat_member")
logger = getLogger("kita.chat_member")


@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_block_bot(
    event: ChatMemberUpdated,
    session: FromDishka[AsyncSession],
    user_service: FromDishka[UserService],
):
    user_id = event.from_user.id
    async with session.begin():
        await user_service.update(user_id, is_bot_blocked=True)

    logger.info("UserID %s blocked the bot.", user_id)

@router.error(ExceptionTypeFilter(UnknownIntent), F.update.callback_query.as_("callback"))
async def unknown_intent(
    event: ErrorEvent,
    callback: CallbackQuery,
    translator: FromDishka[Translator],
    notifier: FromDishka[NotifierService],
):
    await callback.answer()

    payload = MessagePayload(i18n_key="warning_unknown_intent")
    strategy = TextSender(
        bot=callback.bot,
        target_id=callback.from_user.id,
        payload=payload,
        translator=translator,
    )

    await notifier.send(strategy)

