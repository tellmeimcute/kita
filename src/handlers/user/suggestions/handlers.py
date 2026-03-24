import asyncio
from logging import getLogger
from typing import List

from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from database.dto import UserDTO
from handlers.keyboards import ReplyKeyboard
from helpers.suggestion_viewer import SuggestionViewerUtils
from helpers.filters import I18nTextFilter
from helpers.message_payload import MessagePayload
from services.notifier import NotifierService
from services.suggestion import SuggestionService
from services.user import UserService

from .state import PostStates

logger = getLogger("kita.user_suggestions")

router = Router(name="suggestions_user")


@router.message(I18nTextFilter("command_suggest_post"))
async def suggest_post(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    notifier: NotifierService,
):
    await state.set_state(PostStates.waiting_for_post)

    payload = MessagePayload(i18n_key="suggestion_wait_media", reply_markup=ReplyKeyboard.cancel())
    await notifier.notify_user(user_dto, payload=payload)


@router.message(PostStates.waiting_for_post)
async def process_suggestion(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: NotifierService,
    user_service: UserService,
    config: Config,
    album: List[Message] | None = None,
):
    suggestion_service = SuggestionService(session, config)

    if not album:
        album = (message,)

    suggestion_dto = await suggestion_service.create(user_dto, album)

    payload = MessagePayload(i18n_key="on_moderation", reply_markup=ReplyKeyboard.main(user_dto))
    await notifier.notify_user(user_dto, payload=payload)

    await state.clear()

    suggestion_utils = SuggestionViewerUtils(config, notifier)

    i18n_kwargs = suggestion_utils.get_i18n_kwargs(suggestion_dto)
    i18n_kwargs.update(command=html.code(f"{_('command_open_solo_view')} {suggestion_dto.id}"))
    payload = MessagePayload(i18n_key="notify_admin_new_suggestion", i18n_kwargs=i18n_kwargs)

    admins = await user_service.get_admins()
    asyncio.create_task(suggestion_utils.notifier.notify_many(admins, payload))


@router.message(I18nTextFilter("command_user_stats"))
async def statistic(
    message: Message,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: NotifierService,
):
    user_id = message.from_user.id
    stats = await SuggestionDAO.get_stats_by_user_id(session, user_id)
    payload = MessagePayload(i18n_key="user_stats", i18n_kwargs=stats._asdict())
    await notifier.notify_user(user_dto, payload=payload)
