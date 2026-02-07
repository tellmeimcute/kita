

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, MagicData
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import SuggestionDAO
from handlers.keyboards import accept_decline_kb, main_kb

from .logics import get_suggestions_logic, show_last_suggestion
from .state import SuggestionViewer

router = Router(name="suggestions_admin")
router.message.filter(
    MagicData(F.event.from_user.id == F.config.ADMIN_ID)
)

#router.message.middleware()

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
    bot: Bot
):
    await message.answer("Начинаем просмотр...", reply_markup=accept_decline_kb)

    raw_suggestion = await show_last_suggestion(message, session, bot)
    if not raw_suggestion:
        return await message.answer("Нет не рассмотренной предложки :(", reply_markup=main_kb)

    suggestion, media_group = raw_suggestion
    await state.set_state(SuggestionViewer.in_viewer)
    await state.set_data({"last": suggestion.id, "media_group": media_group})

@router.message(
    SuggestionViewer.in_viewer,
    (F.text.lower() == "принять") | (F.text.lower() == "отклонить")
)
async def accept_deny_suggestion(
    message: Message, 
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    config: Config,
    with_og_caption: bool = True,
    is_accepted: bool | None = None
):
    text = message.text.lower()

    is_accepted = True if text == "принять" or is_accepted else False

    data = await state.get_data()
    cur_suggestion_id: int = data["last"]

    # Запостить.
    if is_accepted:
        media_group: MediaGroupBuilder = data["media_group"]
        suggestion_caption = "#предложка"
        if with_og_caption and media_group.caption:
            suggestion_caption = f"{media_group.caption}\n\n{suggestion_caption}"

        media_group.caption = f"{suggestion_caption}"
        await bot.send_media_group(config.CHANNEL_ID, media=media_group.build())

    # Обновить в базе.
    async with session.begin():
        await SuggestionDAO.update_by_id(session, cur_suggestion_id, {"accepted": is_accepted})

    # Получаем новый (следующий) suggestion
    raw_suggestion = await show_last_suggestion(message, session, bot)
    if not raw_suggestion:
        await state.clear()
        return await message.answer("Предложка закончилась!", reply_markup=main_kb)
    
    suggestion, media_group = raw_suggestion
    await state.set_data({"last": suggestion.id, "media_group": media_group})

@router.message(
    SuggestionViewer.in_viewer,
    (F.text.lower() == "принять без подписи")
)
async def accept_wo_caption(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    config: Config
):
    await accept_deny_suggestion(message, session, state, bot, config, False, True)