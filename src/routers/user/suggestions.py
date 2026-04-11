import asyncio
from logging import getLogger
from typing import List

from dishka import FromDishka

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto import UserDTO
from ui.keyboards import ReplyKeyboard
from routers.state import SendSuggestionState
from helpers.suggestion_utils import SuggestionUtils
from helpers.filters import I18nTextFilter
from helpers.schemas.message_payload import MessagePayload
from services.notifier import NotifierService
from services.suggestion import SuggestionService
from services.user import UserService


logger = getLogger("kita.user_suggestions")
router = Router(name="suggestions_user")


@router.message(I18nTextFilter("command_suggest_post"))
async def suggest_post(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    notifier: FromDishka[NotifierService],
):
    await state.set_state(SendSuggestionState.waiting_for_post)

    payload = MessagePayload(i18n_key="suggestion_wait_media", reply_markup=ReplyKeyboard.cancel())
    await notifier.notify_user(user_dto, payload=payload)


@router.message(SendSuggestionState.waiting_for_post)
async def process_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_dto: UserDTO,
    user_service: UserService,
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
    suggestion_utils: FromDishka[SuggestionUtils],
    album: List[Message] | None = None,
):
    if not album:
        album = (message,)

    async with session.begin():
        suggestion_dto = await suggestion_service.create(user_dto, album)
        if not suggestion_dto.caption and not suggestion_dto.media:
            await session.rollback()
            await notifier.notify_user(user_dto, MessagePayload(i18n_key="error_media_suggestion"))
            return

    admins = await user_service.get_admins()

    payload = MessagePayload(i18n_key="on_moderation", reply_markup=ReplyKeyboard.main(user_dto))
    await notifier.notify_user(user_dto, payload)

    await state.clear()

    i18n_kwargs = suggestion_utils.get_i18n_kwargs(suggestion_dto)
    i18n_kwargs.update(command=html.code(f"{_('command_open_solo_view')} {suggestion_dto.id}"))
    payload = MessagePayload(i18n_key="notify_admin_new_suggestion", i18n_kwargs=i18n_kwargs)
    asyncio.create_task(notifier.notify_many(admins, payload))


@router.message(I18nTextFilter("command_user_stats"))
async def statistic(
    message: Message,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
):
    stats = await suggestion_service.get_user_stats(user_dto)
    payload = MessagePayload(i18n_key="user_stats", i18n_kwargs=stats.model_dump())
    await notifier.notify_user(user_dto, payload=payload)
