import asyncio
from typing import Any

from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, MediaUnion, Message, MessageId
from loguru import logger

from core.enums import RenderType
from core.exceptions import UnsupportedPayload
from core.i18n_translator import Translator
from database.dto import SuggestionFullDTO, UserDTO, UserProfileDTO
from interfaces import BotRegistryProtocol, MessageNotifierProtocol
from ui.keyboards import ReplyKeyboard
from utils.suggestion_utils import SuggestionUtils

from .base import BaseService

SendTarget = UserDTO | UserProfileDTO | int
MAX_RETRY = 3


class NotifierUtilsMixin:
    __slots__ = ()

    async def exec_with_retry(self, to_exec):
        retries = 0
        while True:
            try:
                return await to_exec()
            except TelegramRetryAfter as e:
                if retries + 1 > MAX_RETRY:
                    logger.error("Message sending rate limiting {} times, giving up", MAX_RETRY)
                    raise
                wait = max(float(e.retry_after), 1.0)
                logger.warning("Message sending rate limiting, retrying in {}", wait)
                await asyncio.sleep(wait)
                retries += 1
            except TelegramAPIError:
                logger.exception("Failed to send message")
                raise

    def _parse_target_id(self, target: SendTarget) -> int:
        if isinstance(target, (UserProfileDTO, UserDTO)):
            return target.user_id
        return target


class MessageNotifier(NotifierUtilsMixin, BaseService):
    __slots__ = ("translator",)

    def __init__(
        self,
        translator: Translator,
        bot_registry: BotRegistryProtocol,
    ):
        super().__init__(bot_registry)
        self.translator = translator

    async def send_text(
        self,
        target: SendTarget,
        i18n_key: str,
        i18n_kwargs: dict | None = None,
        kb: Any | None = None,
    ) -> Message:
        if not i18n_kwargs:
            i18n_kwargs = dict()

        target_id = self._parse_target_id(target)

        return await self.exec_with_retry(
            lambda: self.bot.send_message(
                chat_id=target_id,
                text=self.translator.i18n_text(i18n_key, i18n_kwargs),
                reply_markup=kb,
                disable_notification=True,
                disable_web_page_preview=True,
            )
        )

    async def send_mediagroup(
        self,
        target: SendTarget,
        media: list[MediaUnion],
    ) -> list[Message]:
        target_id = self._parse_target_id(target)
        return await self.exec_with_retry(
            lambda: self.bot.send_media_group(target_id, media, disable_notification=True)
        )

    async def forward(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]:
        target_id = self._parse_target_id(target)
        return await self.exec_with_retry(
            lambda: self.bot.forward_messages(
                chat_id=target_id,
                from_chat_id=source_chat,
                message_ids=message_ids,
            )
        )

    async def copy(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]:
        target_id = self._parse_target_id(target)
        return await self.exec_with_retry(
            lambda: self.bot.copy_messages(
                chat_id=target_id,
                from_chat_id=source_chat,
                message_ids=message_ids,
            )
        )

    async def edit(
        self,
        chat_id: int,
        message_id: int,
        new_text: str,
        new_kb: InlineKeyboardMarkup | None = None,
    ) -> bool | Message:
        return await self.exec_with_retry(
            lambda: self.bot.edit_message_text(
                text=new_text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_kb,
            )
        )


class SuggestionNotifier(NotifierUtilsMixin, BaseService):
    __slots__ = (
        "translator",
        "msg_notifier",
        "utils",
    )

    def __init__(
        self,
        translator: Translator,
        bot_registry: BotRegistryProtocol,
        message_notifier: MessageNotifierProtocol,
        utils: SuggestionUtils,
    ):
        super().__init__(bot_registry)
        self.translator = translator
        self.msg_notifier = message_notifier
        self.utils = utils

    async def _send_suggestion(
        self,
        target_id: int,
        i18n_key: str,
        i18n_kwargs: dict,
        dto: SuggestionFullDTO,
    ):
        if dto.render_type == RenderType.MESSAGE:
            return await self.msg_notifier.send_text(target_id, i18n_key, i18n_kwargs)
        if dto.render_type == RenderType.MEDIAGROUP:
            media = self.utils.get_input_media(dto, i18n_key, i18n_kwargs)
            return await self.msg_notifier.send_mediagroup(target_id, media)
        raise UnsupportedPayload

    async def send_to_admin(
        self,
        admin: SendTarget,
        dto: SuggestionFullDTO,
    ):
        target_id = self._parse_target_id(admin)

        i18n_key = "suggestion_caption"
        i18n_kwargs = self.utils.get_i18n_kwargs(dto)

        msg = await self._send_suggestion(target_id, i18n_key, i18n_kwargs, dto)

        info_key = "suggestion_admin_viewer_info"
        kb = ReplyKeyboard.viewer_admin_action()

        await self.msg_notifier.send_text(target_id, info_key, i18n_kwargs, kb)

        return msg

    async def send_to_channel(self, channel_id: int, dto: SuggestionFullDTO):
        i18n_key = "channel_post_message"
        i18n_kwargs = self.utils.get_i18n_kwargs(dto)
        return await self._send_suggestion(channel_id, i18n_key, i18n_kwargs, dto)
