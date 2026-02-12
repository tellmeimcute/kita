from logging import Logger

from aiogram import Bot
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder, MediaType

from database.roles import UserRole
from handlers.keyboards import (
    accept_decline_kb,
    cancel_kb,
    get_main_kb_by_role,
)


class Notifier:
    def __init__(self, bot: Bot, logger: Logger):
        self.bot = bot
        self.logger = logger

    async def _save_send(
        self,
        target_id: int,
        content: str | list[MediaType],
        kb: ReplyKeyboardMarkup = None,
    ):
        try:
            if isinstance(content, str):
                return await self.bot.send_message(
                    target_id, content, reply_markup=kb, disable_notification=True
                )
            await self.bot.send_media_group(target_id, content, disable_notification=True)
        except Exception as e:
            self.logger.info(
                "Не удалось отправить сообщение пользователю с ID %s, ошибка: %s", target_id, e
            )

    async def answer_user_state_reset(self, target_id: int, target_role: str | UserRole):
        await self._save_send(target_id, "Состояние сброшено.", get_main_kb_by_role(target_role))

    async def answer_user_on_moderation(self, target_id: int, target_role: str | UserRole):
        await self._save_send(
            target_id, "Отправлено на модерацию.", get_main_kb_by_role(target_role)
        )

    async def answer_user_error_media_suggestion(self, target_id: int):
        await self._save_send(target_id, "Отправьте картинки/видео/gif.")

    async def answer_user_wait_for_media(self, target_id: int):
        text = (
            "Отправьте картинки/видео/gif одним постом.\n\n"
            "Отменить действие можно в клавиатуре или командой /cancel"
        )
        await self._save_send(target_id, text, cancel_kb)

    async def answer_admin_user_immune(self, target_id: int):
        await self._save_send(target_id, "Этот пользователь неуязвим.")

    async def answer_admin_user_role_changed(
        self,
        target_id: int,
        username: str,
        user_id: int,
        role: str | UserRole,
    ):
        await self._save_send(
            target_id, f"Пользователю {username} ({user_id}) изменена роль на {role}."
        )

    async def answer_admin_role_not_exist(self, target_id: int):
        await self._save_send(target_id, "Такой роли не существует.")

    async def answer_admin_user_not_found(self, target_id: int, user_id: int):
        await self._save_send(target_id, f"Пользователь с id {user_id} не найден.")

    async def answer_admin_no_active_suggestions(
        self,
        target_id: int,
        target_role: str | UserRole,
    ):
        await self._save_send(
            target_id,
            "Нет не рассмотренной предложки :(",
            get_main_kb_by_role(target_role),
        )

    async def answer_admin_start_review(self, target_id: int):
        await self._save_send(target_id, "Начинаем просмотр...", accept_decline_kb)

    async def notify_user_role_changed(self, target_id, role):
        await self._save_send(
            target_id, f"🤡 Вам назначили роль {role}!", get_main_kb_by_role(role)
        )

    async def notify_admin_new_suggestion(
        self,
        target_id: int,
        username: str,
        user_id: int,
        sug_media_group: MediaGroupBuilder,
    ):
        await self._save_send(target_id, f"Новый пост от @{username} ({user_id}):")
        await self._save_send(target_id, sug_media_group.build())
