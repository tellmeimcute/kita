from dataclasses import dataclass

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dto import UserDTO
from database.repository import SuggestionRepository, UserRepository
from interfaces import UnitOfWorkProtocol


@dataclass(frozen=True)
class RepositoryContext:
    uow: UnitOfWorkProtocol
    user_repo: UserRepository
    suggestion_repo: SuggestionRepository
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
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
        test_user_dto=test_user_dto,
    )

    async with context.uow.transaction():
        await context.user_repo.create(test_user_dto)

    return context
