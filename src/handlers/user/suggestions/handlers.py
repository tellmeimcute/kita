import asyncio
from logging import getLogger
from typing import List

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import SuggestionDAO, UserAlchemyDAO
from database.models import UserAlchemy
from database.dto import UserDTO
from helpers.utils import create_medias
from helpers.message_payload import MessagePayload
from middlewares import MediaGroupMiddleware
from services.notifier import Notifier
from handlers.keyboards import get_main_kb_by_role, cancel_kb

from .logics import notify_admins_task
from .state import PostStates

logger = getLogger("user_suggestions")

router = Router(name="suggestions_user")
router.message.middleware(MediaGroupMiddleware(latency=0.25))


@router.message(F.text == "Предложить пост")
async def suggest_post(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    notifier: Notifier,
):
    await state.set_state(PostStates.waiting_for_post)
    
    payload = MessagePayload(i18n_key="suggestion_wait_media", reply_markup=cancel_kb)
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

    album = album or (message,)
    caption = album[0].caption
    async with session.begin():
        suggestion = await SuggestionDAO.create(
            session, author_id=user_id, media_group_id=media_group_id, caption=caption
        )
        medias = await create_medias(session, album, suggestion)

        if not medias:
            payload =  MessagePayload(i18n_key="error_media_suggestion")
            await notifier.notify_user(user_dto, payload=payload)
            return await session.rollback()
        
    kb = get_main_kb_by_role(user_dto.role)
    payload =  MessagePayload(i18n_key="on_moderation", reply_markup=kb)
    await notifier.notify_user(user_dto, payload=payload)

    await state.clear()

    admins = await UserAlchemyDAO.get_admins(session)
    asyncio.create_task(
        notify_admins_task(suggestion, admins, author, logger, notifier)
    )


@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    user_alchemy: UserAlchemy,
    notifier: Notifier,
    media_group_id: str,
):
    await process_suggestion(
        message, state, session, user_alchemy, notifier, media_group_id, album
    )


@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession, user_dto: UserDTO, notifier: Notifier,):
    user_id = message.from_user.id
    stats = await SuggestionDAO.get_stats_by_user_id(session, user_id)

    i18n_kwargs = {
        "total_user_suggestions": stats.total,
        "accepted_user_suggestions": stats.accepted,
        "declined_user_suggestions": stats.declined,
    }
    payload =  MessagePayload(i18n_key="user_stats", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(user_dto, payload=payload)