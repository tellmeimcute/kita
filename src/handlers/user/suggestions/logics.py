

import asyncio
from typing import List
from logging import Logger

from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from database.models import UserAlchemy


async def notify_admins_task(
    bot: Bot,
    admins: List[UserAlchemy], 
    username: str, 
    user_id: int, 
    media_group: MediaGroupBuilder,
    logger: Logger,
):
    for admin in admins:
        try:
            await bot.send_message(
                chat_id=admin.user_id, text=f"Новый пост от @{username} ({user_id}):"
            )
            await bot.send_media_group(chat_id=admin.user_id, media=media_group.build())
            logger.info(
                "Отправлено уведомление о новом посте админу %s (%s)", admin.username, admin.user_id 
            )
        except Exception as e:
            logger.error(
                "Ошибка при уведомлении админа ID %s username %s: %s", admin.id, admin.username, e
            )
        finally:
            await asyncio.sleep(0.05)