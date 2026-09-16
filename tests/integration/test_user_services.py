from collections.abc import Callable
from dataclasses import dataclass

import pytest
from aiogram.types import User as AiogramUser
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
from usecases.register_user import RegisterResult, UserRegisterOrUpdateUseCase


@dataclass(frozen=True)
class UserTestContext:
    uow: UnitOfWorkProtocol
    user_service: UserServiceProtocol
    profile_service: UserProfileServiceProtocol
    user_redis: UserRedis
    profile_redis: UserProfileRedis
    test_user_dto: UserDTO
    test_user_id: int
    aiogram_user: AiogramUser
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

    aiogram_user = AiogramUser(
        id=test_user_id,
        username=test_user_dto.username,
        first_name=test_user_dto.name,
        is_bot=False,
    )

    return UserTestContext(
        uow=uow,
        user_service=await request_container.get(UserServiceProtocol),
        profile_service=await request_container.get(UserProfileServiceProtocol),
        user_redis=await request_container.get(UserRedis),
        profile_redis=await request_container.get(UserProfileRedis),
        test_user_dto=test_user_dto,
        test_user_id=test_user_id,
        aiogram_user=aiogram_user,
        user_redis_key=user_repo._get_key(test_user_id),
        profile_redis_key=profile_repo._get_key(test_user_id),
    )


async def test_register_user(user_test_context: UserTestContext):
    ctx = user_test_context

    async with ctx.uow.transaction():
        user_dto = await ctx.user_service.get_or_create(ctx.test_user_dto)
        profile_dto = await ctx.profile_service.get_or_create(ctx.test_user_id)
        await ctx.uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert isinstance(profile_dto, UserProfileDTO)
    assert user_dto.user_id == profile_dto.user_id


async def test_redis_stalling_data(user_test_context: UserTestContext):
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
    user_test_context: UserTestContext,
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


async def test_user_services_get_or_create_when_existed_cache(user_test_context: UserTestContext):
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


async def test_register_or_update_usecase(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
):
    ctx = user_test_context
    register_or_update = await request_container.get(UserRegisterOrUpdateUseCase)

    async with ctx.uow.transaction():
        result = await register_or_update.execute(ctx.aiogram_user)
        await ctx.uow.rollback()

    assert isinstance(result, RegisterResult)
    assert isinstance(result.user, UserDTO)
    assert isinstance(result.profile, UserProfileDTO)

    assert result.user.user_id == ctx.test_user_dto.user_id
    assert result.profile.user_id == ctx.test_user_dto.user_id


async def test_register_or_update_usecase_new_username(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
):
    ctx = user_test_context
    register_or_update = await request_container.get(UserRegisterOrUpdateUseCase)

    new_username = "EternalGoonSesh"

    async with ctx.uow.transaction():
        initial_result = await register_or_update.execute(ctx.aiogram_user)

        updated_user = ctx.aiogram_user.model_copy(update={"username": new_username})
        updated_result = await register_or_update.execute(updated_user)

        get_user_dto = await ctx.user_service.get(ctx.test_user_id)

        await ctx.uow.rollback()

    assert initial_result.user.username != updated_result.user.username
    assert updated_result.user.user_id == get_user_dto.user_id
    assert updated_result.user.username == new_username
    assert updated_result.user.username == get_user_dto.username
