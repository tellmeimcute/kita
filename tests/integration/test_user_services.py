from collections.abc import Callable
from dataclasses import dataclass

import pytest
from dishka import AsyncContainer

from database.dto import UserDTO, UserProfileDTO
from database.redis import UserProfileRedis, UserRedis
from database.repository.cached import CachedUserProfileRepository, CachedUserRepository
from interfaces import (
    UnitOfWorkProtocol,
    UserProfileRepositoryProtocol,
    UserProfileServiceProtocol,
    UserRepositoryProtocol,
    UserServiceProtocol,
)


@dataclass(frozen=True)
class TestContext:
    uow: UnitOfWorkProtocol
    user_service: UserServiceProtocol
    profile_service: UserProfileServiceProtocol
    user_redis: UserRedis
    profile_redis: UserProfileRedis
    test_user_dto: UserDTO
    test_user_id: int
    user_redis_key: str
    profile_redis_key: str


@pytest.fixture
async def user_test_context(
    request_container: AsyncContainer, user_dto_factory: Callable[..., UserDTO]
):
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo: CachedUserRepository = await request_container.get(UserRepositoryProtocol)
    profile_repo: CachedUserProfileRepository = await request_container.get(
        UserProfileRepositoryProtocol
    )

    test_user_dto = user_dto_factory()
    test_user_id = test_user_dto.user_id

    return TestContext(
        uow=uow,
        user_service=await request_container.get(UserServiceProtocol),
        profile_service=await request_container.get(UserProfileServiceProtocol),
        user_redis=await request_container.get(UserRedis),
        profile_redis=await request_container.get(UserProfileRedis),
        test_user_dto=test_user_dto,
        test_user_id=test_user_id,
        user_redis_key=user_repo._get_key(test_user_id),
        profile_redis_key=profile_repo._get_key(test_user_id),
    )


async def test_register_user(user_test_context: TestContext):
    """TEST USER MIDDLEWARE CASE"""
    ctx = user_test_context

    async with ctx.uow.transaction():
        user_dto = await ctx.user_service.get_or_create(ctx.test_user_dto)
        profile_dto = await ctx.profile_service.get_or_create(ctx.test_user_id)
        await ctx.uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert isinstance(profile_dto, UserProfileDTO)
    assert user_dto.user_id == profile_dto.user_id


async def test_redis_stalling_data(user_test_context: TestContext):
    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.create(ctx.test_user_dto)
        await ctx.profile_service.create(ctx.test_user_id)
        await ctx.uow.rollback()

    async with ctx.uow.transaction():
        user_dto = await ctx.user_service.get(ctx.test_user_id)
        profile_dto = await ctx.profile_service.get(ctx.test_user_id)
        await ctx.uow.rollback()

    assert user_dto is None
    assert profile_dto is None


async def test_user_services_get_or_create_when_register_dont_cache(
    user_test_context: TestContext,
):
    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.get_or_create(ctx.test_user_dto)
        cached_user = await ctx.user_redis.get(ctx.user_redis_key)

        await ctx.profile_service.get_or_create(ctx.test_user_id)
        cached_profile = await ctx.profile_redis.get(ctx.profile_redis_key)

        await ctx.uow.rollback()

    assert cached_user is None
    assert cached_profile is None


async def test_user_services_get_or_create_when_existed_cache(user_test_context: TestContext):
    ctx = user_test_context

    async with ctx.uow.transaction():
        # 1 Create and dont cache (write path)
        await ctx.user_service.get_or_create(ctx.test_user_dto)
        # Get and cache (read path)
        await ctx.user_service.get_or_create(ctx.test_user_dto)

        cached_user = await ctx.user_redis.get(ctx.user_redis_key)

        # Create and dont cache (write path)
        await ctx.profile_service.get_or_create(ctx.test_user_id)
        # Get and cache (read path)
        await ctx.profile_service.get_or_create(ctx.test_user_id)

        cached_profile = await ctx.profile_redis.get(ctx.profile_redis_key)

        await ctx.uow.rollback()

    assert isinstance(cached_user, UserDTO)
    assert isinstance(cached_profile, UserProfileDTO)
