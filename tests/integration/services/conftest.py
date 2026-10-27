from collections.abc import Callable
from dataclasses import dataclass

import pytest
from aiogram.types import User as AiogramUser
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.dto import UserDTO
from database.redis import UserProfileRedis, UserRedis, UserStatsRedis
from database.repository import UserRepository
from database.repository.cached import (
    CachedSuggestionRepository,
    CachedUserProfileRepository,
    CachedUserRepository,
)
from interfaces import (
    SuggestionRepositoryProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
    UserProfileRepositoryProtocol,
    UserProfileServiceProtocol,
    UserRepositoryProtocol,
    UserServiceProtocol,
)


@dataclass(frozen=True)
class UserTestContext:
    uow: UnitOfWorkProtocol
    user_service: UserServiceProtocol
    profile_service: UserProfileServiceProtocol
    user_redis: UserRedis
    profile_redis: UserProfileRedis
    test_user_dto: UserDTO
    user_redis_key: str
    profile_redis_key: str


@pytest.fixture
async def user_test_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
) -> UserTestContext:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo: CachedUserRepository = await request_container.get(UserRepositoryProtocol)
    profile_repo: CachedUserProfileRepository = await request_container.get(
        UserProfileRepositoryProtocol
    )

    test_user_dto = user_dto_factory()
    test_user_id = test_user_dto.user_id

    return UserTestContext(
        uow=uow,
        user_service=await request_container.get(UserServiceProtocol),
        profile_service=await request_container.get(UserProfileServiceProtocol),
        user_redis=await request_container.get(UserRedis),
        profile_redis=await request_container.get(UserProfileRedis),
        test_user_dto=test_user_dto,
        user_redis_key=user_repo._get_key(test_user_id),
        profile_redis_key=profile_repo._get_key(test_user_id),
    )


@pytest.fixture
def aiogram_user(user_test_context: UserTestContext) -> AiogramUser:
    dto = user_test_context.test_user_dto

    return AiogramUser(
        id=dto.user_id,
        username=dto.username,
        first_name=dto.name,
        is_bot=False,
    )


@dataclass(frozen=True)
class SuggestionServiceContext:
    uow: UnitOfWorkProtocol
    suggestion_service: SuggestionServiceProtocol
    author: UserDTO
    stats_redis: UserStatsRedis
    stats_key: str
    session_maker: async_sessionmaker[AsyncSession]


@pytest.fixture
async def suggestion_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
) -> SuggestionServiceContext:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo = await request_container.get(UserRepository)
    suggestion_repo: CachedSuggestionRepository = await request_container.get(
        SuggestionRepositoryProtocol
    )

    author = user_dto_factory()

    async with uow.transaction():
        await user_repo.create(author)

    return SuggestionServiceContext(
        uow=uow,
        suggestion_service=await request_container.get(SuggestionServiceProtocol),
        author=author,
        stats_redis=await request_container.get(UserStatsRedis),
        stats_key=suggestion_repo._get_user_stats_key(author.user_id),
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
    )
