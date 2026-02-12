import asyncio
from logging import Logger
from typing import List

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder

from database.models import Suggestion, UserAlchemy
from services.notifier import Notifier


async def notify_admins_task(
    suggestion: Suggestion,
    admins: List[UserAlchemy],
    username: str,
    media_group: MediaGroupBuilder,
    logger: Logger,
    notifier: Notifier,
):
    for admin in admins:
        try:
            await notifier.notify_admin_new_suggestion(
                admin.user_id, username, suggestion.author_id, media_group
            )
            logger.info(
                "Отправлено уведомление о новом посте админу %s (%s)",
                admin.username,
                admin.user_id,
            )
        finally:
            await asyncio.sleep(0.05)
