import asyncio
from abc import ABC, abstractmethod
from logging import Logger, getLogger
from itertools import batched

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from database.dto import UserDTO
from helpers.schemas.message_payload import MessagePayload
from helpers.i18n_translator import Translator


logger: Logger = getLogger("kita.notifier_service")


class MessageSender(ABC):
    def __init__(
        self,
        bot: Bot,
        target_id: int,
        payload: MessagePayload,
        silent: bool = True,
        translator: Translator | None = None
    ):
        self.bot = bot
        self.target_id = target_id
        self.silent = silent
        self.payload = payload

        self.translator = translator

    @abstractmethod
    async def send(self) -> Message | list[Message]:
        ...

    @property
    def name(cls):
        return cls.__class__.__qualname__

class MediaGroupSender(MessageSender):
    async def send(self) -> list[Message]:
        return await self.bot.send_media_group(self.target_id, self.payload.content, disable_notification=self.silent)

class TextSender(MessageSender):
    async def send(self) -> Message:
        if not self.translator:
            raise ValueError("Translator is required for TextSender")
        
        content = self.translator.get_i18n_text(self.payload.i18n_key, self.payload.i18n_kwargs)
        return await self.bot.send_message(
            chat_id=self.target_id,
            text=content,
            reply_markup=self.payload.reply_markup,
            disable_notification=self.silent,
        )

class MessageTransfer(MessageSender):
    def __init__(
        self,
        bot: Bot,
        target_id: int,
        from_chat_id: int,
        message_ids: list[int],
    ):
        self.bot = bot
        self.target_id = target_id

        self.from_chat_id = from_chat_id
        self.message_ids = message_ids

class CopyTransfer(MessageTransfer):
    async def send(self):
        return await self.bot.copy_messages(
            chat_id=self.target_id,
            from_chat_id=self.from_chat_id,
            message_ids=self.message_ids,
        )
    
class ForwardTransfer(MessageTransfer):
    async def send(self):
        return await self.bot.forward_messages(
            chat_id=self.target_id,
            from_chat_id=self.from_chat_id,
            message_ids=self.message_ids,
        )

class NotifierService:
    
    __slots__ = (
        "bot",
        "chunk_delay",
        "chunk_size",
        "translator",
    )

    def __init__(
        self,
        bot: Bot,
        translator: Translator,
        chunk_delay: float = 5.0,
        chunk_size: int = 5,
    ):
        self.bot: Bot = bot

        self.chunk_delay = chunk_delay
        self.chunk_size = chunk_size

        self.translator = translator

    def send_strategy_factory(self, target_id: int, payload: MessagePayload, silent: bool = True):
        if payload.i18n_key:
            return TextSender(self.bot, target_id, payload, silent, self.translator)
        if payload.content:
            return MediaGroupSender(self.bot, target_id, payload, silent, self.translator)

        raise ValueError("Unsupported payload format")

    async def send(self, strategy: MessageSender):
        try:
            return await strategy.send()
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning("Failed to execute strategy %s to target %s: %s", strategy.name, strategy.target_id, e)

    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload):
        if user_dto.is_bot_blocked:
            return logger.info(
                "User %s (%s) has blocked the bot. Skip.", user_dto.username, user_dto.user_id
            )
        
        strategy = self.send_strategy_factory(user_dto.user_id, payload)
        return await self.send(strategy)

    async def notify_many(self, users_dto: list[UserDTO], payload: MessagePayload):
        for chunk in batched(users_dto, self.chunk_size):
            tasks = [self.notify_user(user_dto, payload) for user_dto in chunk]
            await asyncio.gather(*tasks)
            await asyncio.sleep(self.chunk_delay)

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

    async def edit_message(self, message: Message, text: str):
        await self.bot.edit_message_text(
            text=text, chat_id=message.chat.id, message_id=message.message_id
        )
