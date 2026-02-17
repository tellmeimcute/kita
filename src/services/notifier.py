from logging import Logger, getLogger

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.media_group import MediaType
from aiogram.exceptions import TelegramForbiddenError

from database.dto import UserDTO
from database.models import UserAlchemy
from database.dao import UserAlchemyDAO
from helpers.message_payload import MessagePayload


class Notifier:
    def __init__(self, bot: Bot, sessionmaker: async_sessionmaker):
        self.bot: Bot = bot
        self.logger: Logger = getLogger("notifier_service")
        self.sessionmaker: async_sessionmaker = sessionmaker

    async def _update_user_bot_ban(self, user_dto: UserDTO):
        session: AsyncSession

        async with self.session_maker() as session:
            async with session.begin():
                data = {"is_bot_blocked": True}
                await UserAlchemyDAO.update_by_id(session, user_dto.user_id, data)

        self.logger.info(
            "It seems like user %s (%s) has blocked the bot. User status updated.",
            user_dto.username, user_dto.user_id
        )

    async def _save_send(
        self,
        user_dto: UserDTO,
        content: str | list[MediaType],
        kb: ReplyKeyboardMarkup = None,
        silent=True,
    ):
        target_id = user_dto.user_id
        try:
            if isinstance(content, str):
                return await self.bot.send_message(
                    target_id, content, reply_markup=kb, disable_notification=silent
                )
            return await self.bot.send_media_group(target_id, content, disable_notification=silent)
        except TelegramForbiddenError:
            await self._update_user_bot_ban(user_dto)

        except Exception as e:
            self.logger.error(
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
        if user.is_bot_blocked:
            return self.logger.info(
                "User %s (%s) has blocked the bot.",
                user.username, user.user_id,
            )
        if payload.i18n_key:
            content = self.get_i18n_text(payload.i18n_key, payload.i18n_kwargs)
            return await self._save_send(user, content, payload.reply_markup)

        return await self._save_send(user, payload.content, payload.reply_markup)
