from logging import Logger

from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder, MediaType

from database.models import UserAlchemy
from database.roles import UserRole
from database.dto import UserDTO

from helpers.message_payload import MessagePayload
from handlers.keyboards import (
    accept_decline_kb,
    cancel_kb,
    get_main_kb_by_role,
)


from aiogram.utils.i18n import gettext as _


class Notifier:
    def __init__(self, bot: Bot, logger: Logger):
        self.bot = bot
        self.logger = logger

    async def _save_send(
        self,
        target_id: int,
        content: str | list[MediaType],
        kb: ReplyKeyboardMarkup = None,
        silent=True,
    ):
        try:
            if isinstance(content, str):
                return await self.bot.send_message(
                    target_id, content, reply_markup=kb, disable_notification=silent
                )
            await self.bot.send_media_group(target_id, content, disable_notification=silent)
        except Exception as e:
            self.logger.info(
                "Не удалось отправить сообщение пользователю с ID %s, ошибка: %s", target_id, e
            )

    def get_translated_text(self, i18n_key: str) -> str:
        return _(i18n_key)

    def get_formatted_text(self, text: str, i18n_kwargs: dict[str, str]) -> str:
        return text.format(**i18n_kwargs)

    def get_i18n_text(self, i18n_key, i18n_kwargs) -> str:
        translated = self.get_translated_text(i18n_key)
        return self.get_formatted_text(translated, i18n_kwargs)

    async def notify_user(self, user: UserAlchemy | UserDTO, payload: MessagePayload):
        if payload.i18n_key:
            content = self.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._save_send(user.user_id, content, payload.reply_markup)

        return await self._save_send(user.user_id, payload.content, payload.reply_markup)
