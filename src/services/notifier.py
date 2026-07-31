
from logging import getLogger
from typing import Literal

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload
from database.dto import SuggestionFullDTO, UserDTO, UserProfileDTO
from ui.keyboards import ReplyKeyboard
from ui.senders import (
    CopyTransfer,
    ForwardTransfer,
    MediaGroupSender,
    TextSender,
)
from ui.senders.base import BaseSender
from ui.suggestion_utils import SuggestionUtils

logger = getLogger("kita.notifier_service")


class NotifierService:

    __slots__ = (
        "_bot",
        "_tl",
        "_suggestion_utils"
    )

    def __init__(self, bot: Bot, translator: Translator, suggestion_utils: SuggestionUtils):
        self._bot = bot
        self._tl = translator
        self._suggestion_utils = suggestion_utils

    def strategy_factory(
        self, target_id: int, payload: MessagePayload, silent: bool = True
    ) -> BaseSender:
        if payload.i18n_key:
            return TextSender(self._bot, target_id, payload, silent, self._tl)
        if payload.media:
            return MediaGroupSender(self._bot, target_id, payload, silent, self._tl)

        raise UnsupportedPayload(payload=payload)

    async def send_suggestion(
        self,
        target: UserDTO | int,
        dto: SuggestionFullDTO,
        mode: Literal["admin_viewer", "channel_post"] = "admin_viewer",
    ):
        if isinstance(target, UserDTO):
            target_id = target.user_id
        elif isinstance(target, int):
            target_id = target
        else:
            raise ValueError("target arg should be UserDTO or INT")

        i18n_key: Literal["suggestion_caption", "channel_post_message"]
        if mode == "admin_viewer":
            i18n_key = "suggestion_caption"
        else:
            i18n_key = "channel_post_message"

        payload = self._suggestion_utils.payload_factory(dto, i18n_key)
        strategy = self.strategy_factory(target_id, payload)
        suggestion_msg = await strategy.send()

        if mode == "admin_viewer":
            i18n_kwargs = self._suggestion_utils.get_i18n_kwargs(dto)
            payload = MessagePayload(
                i18n_key="suggestion_admin_viewer_info",
                i18n_kwargs=i18n_kwargs,
                reply_markup=ReplyKeyboard.viewer_admin_action(),
            )
            strategy = self.strategy_factory(target_id, payload)
            await strategy.send()

        return suggestion_msg

    async def send_text(
        self,
        target: UserDTO | int,
        i18n_key: str,
        i18n_kwargs: dict | None = None,
        kb: ReplyKeyboardMarkup | None = None,
    ):
        if not i18n_kwargs:
            i18n_kwargs = dict()

        payload = MessagePayload(i18n_key=i18n_key, i18n_kwargs=i18n_kwargs, reply_markup=kb)

        if isinstance(target, UserDTO):
            return await self.notify_user(target, payload)
        if isinstance(target, int):
            strategy = self.strategy_factory(target, payload)
            return await strategy.send()

    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload, profile_dto: UserProfileDTO | None = None):
        if profile_dto and profile_dto.is_bot_blocked:
            return logger.info("UserID %s has blocked the bot. Skip.", user_dto.user_id)

        strategy = self.strategy_factory(user_dto.user_id, payload)
        return await strategy.send()

    async def forward_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        strategy = ForwardTransfer(
            bot=self._bot,
            target_id=user_dto.user_id,
            from_chat_id=source,
            message_ids=messages,
        )
        return await strategy.send()

    async def copy_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        strategy = CopyTransfer(
            bot=self._bot,
            target_id=user_dto.user_id,
            from_chat_id=source,
            message_ids=messages,
        )
        return await strategy.send()

    async def edit_message_text(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ):
        await self._bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
        )
