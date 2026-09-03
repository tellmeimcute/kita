import asyncio
from functools import wraps
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


def with_retry(max_retries: int = 3):
    def wrapper(fn):
        @wraps(fn)
        async def decorated(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except TelegramRetryAfter as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error("Telegram rate limiting {} times, giving up", max_retries)
                        raise
                    wait = max(float(e.retry_after), 1.0)
                    logger.warning(e.message)
                    await asyncio.sleep(wait)
                except TelegramAPIError:
                    logger.exception("Failed to send message")
                    raise

        return decorated

    return wrapper


class NotifierUtilsMixin:
    __slots__ = ()

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

    @with_retry(MAX_RETRY)
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
        return await self.bot.send_message(
            chat_id=target_id,
            text=self.translator.i18n_text(i18n_key, i18n_kwargs),
            reply_markup=kb,
            disable_notification=True,
            disable_web_page_preview=True,
        )

    @with_retry(MAX_RETRY)
    async def send_mediagroup(
        self,
        target: SendTarget,
        media: list[MediaUnion],
    ) -> list[Message]:
        target_id = self._parse_target_id(target)
        return await self.bot.send_media_group(target_id, media, disable_notification=True)

    @with_retry(MAX_RETRY)
    async def forward(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]:
        target_id = self._parse_target_id(target)
        return await self.bot.forward_messages(
            chat_id=target_id,
            from_chat_id=source_chat,
            message_ids=message_ids,
        )

    @with_retry(MAX_RETRY)
    async def copy(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]:
        target_id = self._parse_target_id(target)
        return await self.bot.copy_messages(
            chat_id=target_id,
            from_chat_id=source_chat,
            message_ids=message_ids,
        )

    @with_retry(MAX_RETRY)
    async def edit(
        self,
        chat_id: int,
        message_id: int,
        new_text: str,
        new_kb: InlineKeyboardMarkup | None = None,
    ) -> bool | Message:
        return await self.bot.edit_message_text(
            text=new_text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=new_kb,
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
