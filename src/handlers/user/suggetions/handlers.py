
from typing import List

from aiogram import F, Router, Bot
from middlewares.media_group import MediaGroutMiddleware
from .state import PostStates
from .logics import suggestion_logic, statistic_logic


from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from config import Config

router = Router(name="suggestions_user")
router.message.middleware(MediaGroutMiddleware(latency=0.25))

@router.message(F.text == "Предложить пост")
async def propose_post(message: Message, state: FSMContext):
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Отправьте картинки/видео/gif одним постом.")

@router.message(PostStates.waiting_for_post, ~F.media_group_id)
async def process_single_post(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession, 
    bot: Bot,
    config: Config
):
    user_id = message.from_user.id
    username = message.from_user.username
    album = (message,)
    await suggestion_logic(
        session, bot, album, state, user_id, username, config.ADMIN_ID
    )

@router.message(PostStates.waiting_for_post, F.media_group_id)
async def process_media_group_post(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    album: List[Message],
    media_group_id: str,
    bot: Bot,
    config: Config
):
    user_id = message.from_user.id
    username = message.from_user.username
    await suggestion_logic(
        session, bot, album, state, user_id, username, config.ADMIN_ID, media_group_id
    )


@router.message(F.text == "Статистика")
async def statistic(message: Message, session: AsyncSession):
    user_id = message.from_user.id
    return await statistic_logic(message, session, user_id)