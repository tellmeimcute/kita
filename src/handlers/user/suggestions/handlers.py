import asyncio
from logging import getLogger
from typing import List

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO, UserAlchemyDAO
from database.models import UserAlchemy
from helpers.utils import create_medias, get_media_group
from middlewares import MediaGroupMiddleware
from services.notifier import Notifier

from .logics import notify_admins_task
from .state import PostStates

logger = getLogger("user_suggestions")

router = Router(name="suggestions_user")
router.message.middleware(MediaGroupMiddleware(latency=0.25))


@router.message(F.text == "Предложить пост")
async def suggest_post(
    message: Message,
    state: FSMContext,
    notifier: Notifier,
):
    await state.set_state(PostStates.waiting_for_post)
    await notifier.notify_user_wait_for_media(message.from_user.id)


@router.message(PostStates.waiting_for_post, ~F.media_group_id)
async def process_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    user_alchemy: UserAlchemy,
    notifier: Notifier,
    media_group_id: int | None = None,
    album: List[Message] | None = None,
):
    user_id = message.from_user.id
    username = message.from_user.username

    album = album or (message,)
    caption = album[0].caption
    async with session.begin():
        suggestion = await SuggestionDAO.create(
            session, author_id=user_id, media_group_id=media_group_id, caption=caption
        )
        medias = await create_medias(session, album, suggestion)

        if not medias:
            await session.rollback()
            return await notifier.notify_user_error_media_suggestion(user_alchemy.user_id)

    media_group = get_media_group(medias, caption)

    await notifier.notify_user_on_moderation(user_alchemy.user_id, user_alchemy.role)
    await state.clear()

    admins = await UserAlchemyDAO.get_admins(session)
    asyncio.create_task(notify_admins_task(bot, admins, username, user_id, media_group, logger))


@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    user_alchemy: UserAlchemy,
    notifier: Notifier,
    media_group_id: str,
    bot: Bot,
):
    await process_suggestion(
        message, state, session, bot, user_alchemy, notifier, media_group_id, album
    )


@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    stats = await SuggestionDAO.get_stats_by_user_id(session, user_id)

    await message.answer(
        f"Постов предожено: {stats.total}\n\n"
        f"✅ Принято: {stats.accepted}\n"
        f"❌Отклонено: {stats.declined}"
    )
