from typing import List, Sequence

from aiogram import F, Router, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.utils.media_group import MediaGroupBuilder

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserAlchemy, Suggestion
from middlewares.media_group import MediaGroutMiddleware

from database.dao.user import UserAlchemyDAO
from database.dao.suggestion import SuggestionDAO

from helpers.utils import build_album_suggestions

ADMIN_TGID = 1574316170


class PostStates(StatesGroup):
    waiting_for_post = State()


router = Router()
router.message.middleware(MediaGroutMiddleware(latency=0.25))


###
###         START HANDLER (TODO: MOVE TO ANOTHER FILE)
###
@router.message(CommandStart())
async def start(message: Message, user_alchemy: UserAlchemy, session: AsyncSession):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Предложить пост")],
            [KeyboardButton(text="Статистика")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    return message.answer(f"{user_alchemy}", reply_markup=keyboard)


###
###         MADE A SUGGESTION HANDLER
###
@router.message(F.text == "Предложить пост")
async def propose_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Отправьте картинки/видео/gif одним постом.")


###
###         SUGGESTION HANDLERS
###


async def suggestion_logic(
    session: AsyncSession,
    bot: Bot,
    album: Sequence[Message],
    state: State,
    user_id: int,
    username: str,
    media_group_id: str | None = None,
):
    suggestion, medias, media_group = build_album_suggestions(album, user_id, media_group_id)

    if not len(medias):
        return await bot.send_message(
            chat_id=user_id, text="Отправьте картинки/видео/gif."
        )

    await bot.send_message(
        chat_id=ADMIN_TGID, text=f"Новый пост от @{username} ({user_id}):"
    )

    await bot.send_media_group(chat_id=ADMIN_TGID, media=media_group.build())

    await bot.send_message(chat_id=user_id, text="Отправлено.")

    await state.clear()

    async with session.begin():
        session.add_all((suggestion, *medias))


@router.message(PostStates.waiting_for_post, ~F.media_group_id)
async def process_single_post(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
):
    user_id = message.from_user.id
    username = message.from_user.username
    album = (message,)
    await suggestion_logic(
        session, bot, album, state, user_id, username
    )


@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_post(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    media_group_id: str,
    bot: Bot,
):
    user_id = message.from_user.id
    username = message.from_user.username
    await suggestion_logic(
        session, bot, album, state, user_id, username, media_group_id
    )


###
###         ACCOUNT STATS HANDLER
###
@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession):
    user_id = message.from_user.id

    async with session.begin():
        user_suggestions = await SuggestionDAO.get(session, Suggestion.author_id == user_id, Suggestion.id.desc())
        user_suggestions_count = await SuggestionDAO.count(session, Suggestion.author_id == user_id)

    await message.answer(
        f"Постов предожено: {user_suggestions_count}.\n{user_suggestions}"
    )


#
#   TODO: ПЕРЕМЕСТИТЬ В АДМИН ХЕНДЛЕРЫ
#
@router.message(Command("get_suggestion"))
async def get_suggestion(message: Message, session: AsyncSession, command: CommandObject):
    if message.from_user.id != ADMIN_TGID:
        return

    suggestion_id = command.args

    async with session.begin():
        suggestion: Suggestion = await SuggestionDAO.get_one_or_none_with_children(
            session, Suggestion.media, Suggestion.id == suggestion_id
        )

    if not suggestion:
        return
    medias = suggestion.media

    media_group = MediaGroupBuilder(
        caption=suggestion.caption
    )

    for media in medias:
        media_group.add(type=media.filetype, media=media.telegram_file_id)

    author = await UserAlchemyDAO.get_one_or_none_by_id(session, suggestion.author_id)
    await message.bot.send_message(
        message.chat.id,
        f"Предложка от @{author.username} ({suggestion.author_id}):"
    )

    await message.bot.send_media_group(
        message.chat.id,
        media=media_group.build()
    )
