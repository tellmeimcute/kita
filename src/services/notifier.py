
from logging import getLogger

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import Message, InlineKeyboardMarkup

from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload

from database.dto import UserDTO

from ui.senders import (
    MessageSender,
    MessageTransfer,
    TextSender,
    MediaGroupSender,
    CopyTransfer,
    ForwardTransfer,
)

logger = getLogger("kita.notifier_service")


class NotifierService:
    
    __slots__ = (
        "bot",
        "translator",
    )

    def __init__(self, bot: Bot, translator: Translator):
        self.bot = bot
        self.translator = translator

    def strategy_factory(self, target_id: int, payload: MessagePayload, silent: bool = True):
        if payload.i18n_key:
            return TextSender(self.bot, target_id, payload, silent, self.translator)
        if payload.media:
            return MediaGroupSender(self.bot, target_id, payload, silent, self.translator)

        raise UnsupportedPayload(payload=payload)

    async def send(self, strategy: MessageSender | MessageTransfer) -> list[Message] | Message | None:
        try:
            return await strategy.send()
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning("Failed to execute strategy %s to target %s: %s", strategy.name, strategy.target_id, e)

    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload):
        if user_dto.is_bot_blocked:
            return logger.info("UserID %s has blocked the bot. Skip.", user_dto.user_id)
        
        strategy = self.strategy_factory(user_dto.user_id, payload)
        return await self.send(strategy)

    async def forward_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        strategy = ForwardTransfer(
            bot=self.bot,
            target_id=user_dto.user_id,
            from_chat_id=source,
            message_ids=messages,
        )
        return await self.send(strategy)

    async def copy_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        strategy = CopyTransfer(
            bot=self.bot,
            target_id=user_dto.user_id,
            from_chat_id=source,
            message_ids=messages,
        )
        return await self.send(strategy)

    async def edit_message_text(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ):
        await self.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
        )
