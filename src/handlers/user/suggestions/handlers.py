import asyncio
from logging import getLogger
from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import lazy_gettext as __
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from handlers.keyboards import get_cancel_kb, get_main_kb_by_role
from helpers.filters import I18nTextFilter
from helpers.message_payload import MessagePayload
from helpers.utils import create_medias
from middlewares import MediaGroupMiddleware
from services.notifier import Notifier

from .logics import notify_admins_task
from .state import PostStates

logger = getLogger("user_suggestions")

router = Router(name="suggestions_user")
router.message.middleware(MediaGroupMiddleware(latency=0.25))


@router.message(I18nTextFilter("command_suggest_post"))
async def suggest_post(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    notifier: Notifier,
):
    await state.set_state(PostStates.waiting_for_post)

    payload = MessagePayload(i18n_key="suggestion_wait_media", reply_markup=get_cancel_kb())
    await notifier.notify_user(user_dto, payload=payload)


@router.message(PostStates.waiting_for_post, ~F.media_group_id)
async def process_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: Notifier,
    media_group_id: int | None = None,
    album: List[Message] | None = None,
):
    author = message.from_user
    user_id = author.id

    if not album:
        album = (message,)

    first = album[0]
    caption = first.caption or first.text

    async with session.begin():
        suggestion = await SuggestionDAO.create(
            session, author_id=user_id, media_group_id=media_group_id, caption=caption
        )
        medias = await create_medias(session, album, suggestion)

        if not medias and not caption:
            payload = MessagePayload(i18n_key="error_media_suggestion")
            await notifier.notify_user(user_dto, payload=payload)
            return await session.rollback()

    kb = get_main_kb_by_role(user_dto.role)
    payload = MessagePayload(i18n_key="on_moderation", reply_markup=kb)
    await notifier.notify_user(user_dto, payload=payload)

    await state.clear()

    admins = await UserAlchemyDAO.get_admins(session)
    asyncio.create_task(notify_admins_task(suggestion, admins, author, logger, notifier))


@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    user_dto: UserDTO,
    notifier: Notifier,
    media_group_id: str,
):
    await process_suggestion(message, state, session, user_dto, notifier, media_group_id, album)


@router.message(I18nTextFilter("command_user_stats"))
async def statistic(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: Notifier,
):
    user_id = message.from_user.id
    stats = await SuggestionDAO.get_stats_by_user_id(session, user_id)

    i18n_kwargs = {
        "total_user_suggestions": stats.total,
        "accepted_user_suggestions": stats.accepted,
        "declined_user_suggestions": stats.declined,
    }
    payload = MessagePayload(i18n_key="user_stats", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(user_dto, payload=payload)
