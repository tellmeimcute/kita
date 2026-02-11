from aiogram import Bot

from handlers.keyboards import (
    accept_decline_kb,
    cancel_kb,
    get_main_kb_by_role,
)


class Notifier:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def notify_user_state_reset(self, target_id, target_role):
        await self.bot.send_message(
            target_id, "Состояние сброшено.", reply_markup=get_main_kb_by_role(target_role)
        )

    async def notify_user_role_changed(self, target_id, role):
        await self.bot.send_message(
            target_id,
            f"🤡 Вам назначили роль {role}!",
            reply_markup=get_main_kb_by_role(role),
        )

    async def notify_user_on_moderation(self, target_id, target_role):
        await self.bot.send_message(
            target_id, "Отправлено на модерацию.", reply_markup=get_main_kb_by_role(target_role)
        )

    async def notify_user_error_media_suggestion(self, target_id):
        await self.bot.send_message(target_id, "Отправьте картинки/видео/gif.")

    async def notify_user_wait_for_media(self, target_id):
        text = (
            "Отправьте картинки/видео/gif одним постом.\n\n"
            "Отменить действие можно в клавиатуре или командой /cancel"
        )
        await self.bot.send_message(target_id, text, reply_markup=cancel_kb)

    async def notify_admin_user_immune(self, target_id):
        await self.bot.send_message(target_id, f"Этот пользователь неуязвим.")

    async def notify_admin_user_role_changed(self, target_id, username, user_id, role):
        await self.bot.send_message(
            target_id, f"Пользователю {username} ({user_id}) изменена роль на {role}."
        )

    async def notify_admin_role_not_exist(self, target_id):
        await self.bot.send_message(target_id, "Такой роли не существует.")

    async def notify_admin_user_not_found(self, target_id, user_id):
        await self.bot.send_message(target_id, f"Пользователь с id {user_id} не найден.")

    async def notify_admin_no_active_suggestions(self, target_id, target_role):
        await self.bot.send_message(
            target_id,
            "Нет не рассмотренной предложки :(",
            reply_markup=get_main_kb_by_role(target_role),
        )

    async def notify_admin_start_review(self, target_id):
        await self.bot.send_message(
            target_id, "Начинаем просмотр...", reply_markup=accept_decline_kb
        )
