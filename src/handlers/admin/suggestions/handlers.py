

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.models import Suggestion, UserAlchemy
from database.dao import SuggestionDAO
from handlers.keyboards import accept_decline_kb, get_main_kb_by_role
from middlewares import AdminMiddleware

from .logics import get_suggestions_logic, get_active_suggestion, post_in_channel
from .state import SuggestionViewer

router = Router(name="suggestions_admin")

# router.message.filter(
#     MagicData(F.event.from_user.id == F.config.ADMIN_ID)
# )

router.message.middleware(AdminMiddleware())

@router.message(Command("get_suggestion", prefix='/!'))
async def get_suggestion(
    message: Message, 
    session: AsyncSession,
    command: CommandObject,
    bot: Bot
):
    suggestion_id = command.args
    await get_suggestions_logic(message, session, bot, suggestion_id)


@router.message(F.text.lower() == "смотреть предложку")
async def show_suggestions_admin_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    bot: Bot
):
    raw_suggestion = await get_active_suggestion(session)
    if not raw_suggestion:
        main_kb = get_main_kb_by_role(user_alchemy.role)
        return await message.answer("Нет не рассмотренной предложки :(", reply_markup=main_kb)

    await message.answer("Начинаем просмотр...", reply_markup=accept_decline_kb)

    suggestion, media_group = raw_suggestion
    await bot.send_media_group(message.chat.id, media_group.build())

    await state.set_state(SuggestionViewer.in_viewer)
    await state.set_data(
        {"last": suggestion.id, "media_group": media_group, "suggestion": suggestion}
    )

@router.message(
    SuggestionViewer.in_viewer,
    (F.text.lower() == "принять") | (F.text.lower() == "отклонить")
)
async def accept_deny_suggestion(
    message: Message, 
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config,
    with_caption: bool = True,
    is_accepted: bool = False
):
    text = message.text.lower()
    is_accepted = text == "принять" or is_accepted

    data = await state.get_data()
    cur_suggestion_id: int = data["last"]

    # Запостить.
    if is_accepted:
        cur_media_group: MediaGroupBuilder = data["media_group"]
        cur_suggestion: Suggestion = data["suggestion"]
        await post_in_channel(bot, cur_media_group, cur_suggestion, config.CHANNEL_ID, with_caption)

    # Обновить в базе.
    async with session.begin():
        await SuggestionDAO.update_by_id(session, cur_suggestion_id, {"accepted": is_accepted})

    # Получаем новый (следующий) suggestion
    raw_suggestion = await get_active_suggestion(session)
    if not raw_suggestion:
        await state.clear()
        main_kb = get_main_kb_by_role(user_alchemy.role)
        return await message.answer("Предложка закончилась!", reply_markup=main_kb)
    
    suggestion, media_group = raw_suggestion
    await bot.send_media_group(message.chat.id, media_group.build())
    
    await state.set_data(
        {"last": suggestion.id, "media_group": media_group, "suggestion": suggestion}
    )

@router.message(
    SuggestionViewer.in_viewer, (F.text.lower() == "принять без подписи")
)
async def accept_wo_caption(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    user_alchemy: UserAlchemy,
    config: Config
):
    await accept_deny_suggestion(message, session, state, bot, user_alchemy, config, False, True)