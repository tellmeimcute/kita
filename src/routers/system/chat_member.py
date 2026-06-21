from logging import getLogger

from aiogram import Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated
from dishka import FromDishka
from sqlalchemy.ext.asyncio import AsyncSession

from services import UserService

router = Router(name="chat_member")
logger = getLogger("kita.chat_member")


@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_block_bot(
    event: ChatMemberUpdated,
    session: FromDishka[AsyncSession],
    user_service: FromDishka[UserService],
):
    user_id = event.from_user.id
    async with session.begin():
        await user_service.update(user_id, is_bot_blocked=True)

    logger.info("UserID %s blocked the bot.", user_id)
