from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dto import UserDTO
from database.repository import SuggestionRepository, UserProfileRepository, UserRepository
from interfaces import UnitOfWorkProtocol, UserBotRepositoryProtocol, UserBotServiceProtocol

from ..scaffold import BOT_ID, BotStack, make_tg_bot, make_tg_channel, seed_userbot


@dataclass(frozen=True)
class RepositoryContext:
    uow: UnitOfWorkProtocol
    user_repo: UserRepository
    suggestion_repo: SuggestionRepository
    profile_repo: UserProfileRepository
    userbot_repo: UserBotRepositoryProtocol
    userbot_service: UserBotServiceProtocol
    session_maker: async_sessionmaker[AsyncSession]
    test_user_dto: UserDTO
    owner_id: int


@pytest.fixture
async def repository_context(
    request_container: AsyncContainer,
    test_user_dto: UserDTO,
) -> RepositoryContext:
    uow = await request_container.get(UnitOfWorkProtocol)
    userbot_service = await request_container.get(UserBotServiceProtocol)

    context = RepositoryContext(
        uow=uow,
        user_repo=await request_container.get(UserRepository),
        suggestion_repo=await request_container.get(SuggestionRepository),
        profile_repo=await request_container.get(UserProfileRepository),
        userbot_repo=await request_container.get(UserBotRepositoryProtocol),
        userbot_service=userbot_service,
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
        test_user_dto=test_user_dto,
        owner_id=test_user_dto.user_id,
    )

    async with context.uow.transaction():
        await context.user_repo.create(test_user_dto)
    await seed_userbot(uow, userbot_service, owner_id=test_user_dto.user_id)

    return context


@pytest.fixture
def foreign_bot(bots: BotStack) -> MagicMock:
    bot = make_tg_bot(make_tg_channel())
    bot.id = BOT_ID + 1
    bots.cache.put(bot)

    return bot
