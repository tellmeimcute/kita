from logging import Logger, getLogger

from typing import Literal, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ReplyKeyboardMarkup, Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.media_group import MediaType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.models import UserAlchemy
from helpers.message_payload import MessagePayload


class Notifier:
    def __init__(self, bot: Bot, sessionmaker: async_sessionmaker):
        self.bot: Bot = bot
        self.sessionmaker: async_sessionmaker = sessionmaker
        self.logger: Logger = getLogger("notifier_service")

    async def _handle_blocked_user(self, user_dto: UserDTO):
        session: AsyncSession

        async with self.sessionmaker() as session:
            async with session.begin():
                data = {"is_bot_blocked": True}
                await UserAlchemyDAO.update_by_id(session, user_dto.user_id, data)

        self.logger.info(
            "User %s (%s) blocked the bot. Status updated.",
            user_dto.username, user_dto.user_id
        )

    async def _safe_send(
        self,
        content: str | list[MediaType],
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
        method: Literal["media_group", "string"] = "string",
        kb: Optional[ReplyKeyboardMarkup] = None,
        silent: bool = True,
    ):
        payload = user_dto, channel_id
        if not any(payload) or all(payload):
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
            await self._handle_blocked_user(user_dto)
        except Exception as e:
            self.logger.error(
                "Failed to send message to target %s: %s", target, e
            )
        
        return None

    async def _deliver_message(
        self,
        message: Message,
        user_dto: Optional[UserDTO] = None,
        channel_id: Optional[int] = None,
        method: Literal["forward", "copy"] = "forward",
    ):
        payload = user_dto, channel_id
        if not any(payload) or all(payload):
            raise ValueError("only one UserDTO or channel_id should be provided")
        target = channel_id if channel_id else user_dto.user_id

        send_func = (
            self.bot.forward_message if method == "forward" else self.bot.copy_message
        )

        try:
            return await send_func(
                chat_id=target,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
        except Exception as e:
            self.logger.error(
                "Failed to %s message to target %s: %s", 
                method, target, e
            )

        return None

    def get_translated_text(self, i18n_key: str) -> str:
        return _(i18n_key)

    def get_formatted_text(self, text: str, i18n_kwargs: dict[str, str]) -> str:
        return text.format(**i18n_kwargs)

    def get_i18n_text(self, i18n_key, i18n_kwargs) -> str:
        translated = self.get_translated_text(i18n_key)
        return self.get_formatted_text(translated, i18n_kwargs)

    async def notify_user(self, user: UserAlchemy | UserDTO, payload: MessagePayload):
        if user.is_bot_blocked:
            return self.logger.info(
                "User %s (%s) has blocked the bot. Skip.",
                user.username, user.user_id,
            )
        
        # STRING message
        if payload.i18n_key:
            content = self.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._safe_send(content, user_dto=user, kb=payload.reply_markup)
        
        # MEDIA GROUP message
        return await self._safe_send(
            payload.content, user_dto=user, method="media_group", kb=payload.reply_markup
        )

    async def forward_message(self, user_dto: UserDTO, message: Message):
        return await self._deliver_message(message, user_dto=user_dto, method="forward")
        
    async def copy_message(self, user_dto: UserDTO, message: Message):
        return await self._deliver_message(message, user_dto=user_dto, method="copy")
        
    async def edit_message(self, message: Message, text: str):
        await self.bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=message.message_id
        )

    async def send_channel(self, channel_id: int, payload: MessagePayload):
        if payload.i18n_key:
            content = self.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._safe_send(
                content, channel_id=channel_id, kb=payload.reply_markup
            )
        
        # MEDIA GROUP message
        return await self._safe_send(
            payload.content, channel_id=channel_id, method="media_group", kb=payload.reply_markup
        )