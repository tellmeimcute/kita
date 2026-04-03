import asyncio
from logging import Logger, getLogger
from typing import Callable, Optional
from itertools import batched

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from database.dto import UserDTO
from helpers.schemas.message_payload import MessagePayload
from helpers.i18n_translator import Translator


logger: Logger = getLogger("kita.notifier_service")


class MessageSender:
    def __init__(self, bot: Bot, payload: MessagePayload, translator: Translator | None = None):
        self.bot = bot
        self.payload = payload

        self.translator = translator

    async def send(self, target_id: int, silent: bool = True) -> Message:
        ...

class MediaGroupSender(MessageSender):
    async def send(self, target_id: int, silent: bool = True) -> list[Message]:
        return await self.bot.send_media_group(target_id, self.payload.content, disable_notification=silent)

class TextSender(MessageSender):
    async def send(self, target_id: int, silent: bool = True) -> Message:
        content = self.translator.get_i18n_text(self.payload.i18n_key, self.payload.i18n_kwargs)
        return await self.bot.send_message(
            chat_id=target_id,
            text=content,
            reply_markup=self.payload.reply_markup,
            disable_notification=silent
        )

class NotifierService:
    
    __slots__ = (
        "bot",
        'sessionmaker',
        "chunk_delay",
        "chunk_size",
        "translator",
    )

    def __init__(
        self,
        bot: Bot,
        chunk_delay: float = 5.0,
        chunk_size: int = 5,
    ):
        self.bot: Bot = bot

        self.chunk_delay = chunk_delay
        self.chunk_size = chunk_size

        self.translator = Translator()

    def _get_send_strategy(self, payload: MessagePayload):
        if payload.i18n_key:
            return TextSender(self.bot, payload, self.translator)
        if payload.content:
            return MediaGroupSender(self.bot, payload, self.translator)

    async def _safe_send(
        self,
        payload: MessagePayload,
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
        silent: bool = True,
    ):
        if (user_dto is None) == (channel_id is None):
            raise ValueError("only one UserDTO or channel_id should be provided")

        target = channel_id if channel_id else user_dto.user_id
        strategy = self._get_send_strategy(payload)

        try:
            return await strategy.send(target, silent)
        except TelegramForbiddenError:
            logger.warning("Forbidden send to target %s", target)

    async def _deliver_messages(
        self,
        method: Callable,
        message_ids: list[int],
        message_source: int,
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
    ):
        """method should be bot.forward_messages or bot.copy_messages"""
        if (user_dto is None) == (channel_id is None):
            raise ValueError("only one UserDTO or channel_id should be provided")
        
        target = channel_id if channel_id else user_dto.user_id

        try:
            return await method(chat_id=target, from_chat_id=message_source, message_ids=message_ids)
        except TelegramForbiddenError as e:
            logger.error("Failed to forwards/copy message to target %s: %s", target, e)

    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload):
        if user_dto.is_bot_blocked:
            return logger.info(
                "User %s (%s) has blocked the bot. Skip.", user_dto.username, user_dto.user_id
            )
        
        return await self._safe_send(payload, user_dto=user_dto)

    async def notify_many(self, users_dto: list[UserDTO], payload: MessagePayload):
        for chunk in batched(users_dto, self.chunk_size):
            tasks = [self.notify_user(user_dto, payload) for user_dto in chunk]
            await asyncio.gather(*tasks)
            await asyncio.sleep(self.chunk_delay)

    async def send_channel(self, channel_id: int, payload: MessagePayload):
        return await self._safe_send(payload, channel_id=channel_id)

    async def forward_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        method = self.bot.forward_messages
        return await self._deliver_messages(method, messages, source, user_dto=user_dto)

    async def copy_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        method = self.bot.copy_messages
        return await self._deliver_messages(method, messages, source, user_dto=user_dto)

    async def edit_message(self, message: Message, text: str):
        await self.bot.edit_message_text(
            text=text, chat_id=message.chat.id, message_id=message.message_id
        )
