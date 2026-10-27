from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dto import UserDTO
from database.repository import SuggestionRepository, UserProfileRepository, UserRepository
from interfaces import UnitOfWorkProtocol

from ..scaffold import BOT_ID, FakeBotRegistry, make_tg_bot, make_tg_channel


@dataclass(frozen=True)
class RepositoryContext:
    uow: UnitOfWorkProtocol
    user_repo: UserRepository
    suggestion_repo: SuggestionRepository
    profile_repo: UserProfileRepository
    session_maker: async_sessionmaker[AsyncSession]
    test_user_dto: UserDTO


@pytest.fixture
async def repository_context(
    request_container: AsyncContainer,
    test_user_dto: UserDTO,
) -> RepositoryContext:
    context = RepositoryContext(
        uow=await request_container.get(UnitOfWorkProtocol),
        user_repo=await request_container.get(UserRepository),
        suggestion_repo=await request_container.get(SuggestionRepository),
        profile_repo=await request_container.get(UserProfileRepository),
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
        test_user_dto=test_user_dto,
    )

    async with context.uow.transaction():
        await context.user_repo.create(test_user_dto)

    return context


@pytest.fixture
def foreign_bot(bot_registry: FakeBotRegistry) -> MagicMock:
    bot = make_tg_bot(make_tg_channel())
    bot.id = BOT_ID + 1
    bot_registry.register(bot)

    return bot
