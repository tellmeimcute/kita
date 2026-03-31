import asyncio
from logging import Logger, getLogger
from typing import Literal, Optional
from itertools import batched

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.media_group import MediaType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dto import UserDTO
from database.dao import UserAlchemyDAO
from helpers.message_payload import MessagePayload
from helpers.i18n_translator import Translator


logger: Logger = getLogger("kita.notifier_service")

class NotifierService:
    RETRY_TIMEOUT_BUFFER = 0.1

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
        sessionmaker: async_sessionmaker,
        chunk_delay: float = 3.0,
        chunk_size: int = 5,
    ):
        self.bot: Bot = bot
        self.sessionmaker: async_sessionmaker = sessionmaker
        
        self.chunk_delay = chunk_delay
        self.chunk_size = chunk_size

        self.translator = Translator()

    async def _handle_blocked_user(self, user_dto: UserDTO):
        session: AsyncSession

        async with self.sessionmaker() as session:
            async with session.begin():
                data = {"is_bot_blocked": True}
                await UserAlchemyDAO.update_by_id(session, user_dto.user_id, data)

    async def _safe_send(
        self,
        content: str | list[MediaType],
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
        method: Literal["media_group", "string"] = "string",
        kb: Optional[ReplyKeyboardMarkup] = None,
        silent: bool = True,
    ):
        if (user_dto is None) == (channel_id is None):
            raise ValueError("only one UserDTO or channel_id should be provided")

        target = channel_id if channel_id else user_dto.user_id

        try:
            if method == "string":
                return await self.bot.send_message(
                    target, content, reply_markup=kb, disable_notification=silent
                )
            if method == "media_group":
                return await self.bot.send_media_group(
                    target, content, disable_notification=silent
                )
        except TelegramForbiddenError:
            if user_dto is not None:
                await self._handle_blocked_user(user_dto)
                logger.info(
                    "User %s (%s) blocked the bot. Status updated", user_dto.username, user_dto.user_id
                )
            else:
                logger.warning("Forbidden on channel %s", channel_id)
        except TelegramRetryAfter as e:
            logger.warning("Rate limit exceeded. Sleeping for %s seconds", e.retry_after)
            await asyncio.sleep(e.retry_after + self.RETRY_TIMEOUT_BUFFER)
            return await self._safe_send(content, user_dto, channel_id, method, kb, silent)
        except Exception as e:
            logger.error("Failed to send message to target %s: %s", target, e)

        return None

    async def _deliver_messages(
        self,
        message_ids: list[int],
        message_source: int,
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
        method: Literal["forward", "copy"] = "forward",
    ):
        if (user_dto is None) == (channel_id is None):
            raise ValueError("only one UserDTO or channel_id should be provided")
        target = channel_id if channel_id else user_dto.user_id

        send_func = self.bot.forward_messages if method == "forward" else self.bot.copy_messages

        try:
            return await send_func(
                chat_id=target,
                from_chat_id=message_source,
                message_ids=message_ids,
            )
        except Exception as e:
            logger.error("Failed to %s message to target %s: %s", method, target, e)

        return None

    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload):
        if user_dto.is_bot_blocked:
            return logger.info(
                "User %s (%s) has blocked the bot. Skip.",
                user_dto.username,
                user_dto.user_id,
            )

        if payload.i18n_key:
            content = self.translator.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._safe_send(content, user_dto=user_dto, kb=payload.reply_markup)

        return await self._safe_send(
            payload.content, user_dto=user_dto, method="media_group", kb=payload.reply_markup
        )

    async def notify_many(self, users_dto: list[UserDTO], payload: MessagePayload):
        for chunk in batched(users_dto, self.chunk_size):
            tasks = [self.notify_user(user_dto, payload) for user_dto in chunk]
            await asyncio.gather(*tasks)
            await asyncio.sleep(self.chunk_delay)

    async def forward_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        return await self._deliver_messages(messages, source, user_dto=user_dto, method="forward")

    async def copy_messages(self, user_dto: UserDTO, messages: list[int], source: int):
        return await self._deliver_messages(messages, source, user_dto=user_dto, method="copy")

    async def edit_message(self, message: Message, text: str):
        await self.bot.edit_message_text(
            text=text, chat_id=message.chat.id, message_id=message.message_id
        )

    async def send_channel(self, channel_id: int, payload: MessagePayload):
        if payload.i18n_key:
            content = self.translator.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._safe_send(content, channel_id=channel_id, kb=payload.reply_markup)

        # MEDIA GROUP message
        return await self._safe_send(
            payload.content, channel_id=channel_id, method="media_group", kb=payload.reply_markup
        )
