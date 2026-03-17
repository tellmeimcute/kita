import asyncio
from logging import Logger
from typing import List

from aiogram import html
from aiogram.utils.i18n import gettext as _
from aiogram.types import User as UserTelegram

from database.models import Suggestion, UserAlchemy
from helpers.message_payload import MessagePayload
from services.notifier import NotifierService


async def notify_admins_task(
    suggestion: Suggestion,
    admins: List[UserAlchemy],
    author: UserTelegram,
    logger: Logger,
    notifier: NotifierService,
):
    for admin in admins:
        try:
            i18n_kwargs = {
                "new_suggestion_id": suggestion.id,
                "new_suggestion_author_id": author.id,
                "new_suggestion_author_username": author.username,
                "new_suggestion_author_fullname": author.full_name,
                "new_suggestion_view_command": html.code(f"{_("command_open_solo_view")} {suggestion.id}"),
            }

            payload = MessagePayload(
                i18n_key="notify_admin_new_suggestion", i18n_kwargs=i18n_kwargs
            )
            await notifier.notify_user(admin, payload=payload)

            logger.info(
                "New suggestion notify sended to %s (%s)",
                admin.username,
                admin.user_id,
            )
        finally:
            await asyncio.sleep(0.05)
