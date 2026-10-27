from aiogram.types import User as AiogramUser
from dishka import AsyncContainer

from database.dto import UserDTO, UserProfileDTO
from usecases.register_user import RegisterResult, UserRegisterOrUpdateUseCase

from .conftest import UserTestContext


async def test_register_user(user_test_context: UserTestContext):
    ctx = user_test_context

    async with ctx.uow.transaction():
        user_dto = await ctx.user_service.get_or_create(ctx.test_user_dto)
        profile_dto = await ctx.profile_service.get_or_create(ctx.test_user_dto.user_id)

    assert isinstance(user_dto, UserDTO)
    assert isinstance(profile_dto, UserProfileDTO)
    assert user_dto.user_id == profile_dto.user_id


async def test_rollback_dont_write_cache(user_test_context: UserTestContext):
    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.get_or_create(ctx.test_user_dto)
        await ctx.profile_service.get_or_create(ctx.test_user_dto.user_id)
        await ctx.uow.rollback()

    async with ctx.uow.transaction():
        user_dto = await ctx.user_service.get(ctx.test_user_dto.user_id)
        profile_dto = await ctx.profile_service.get(ctx.test_user_dto.user_id)

    assert user_dto is None
    assert profile_dto is None


async def test_user_service_get_or_create_redis_stalling_data(user_test_context: UserTestContext):
    """Rollback after read path: redis should be clear"""

    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.get_or_create(ctx.test_user_dto)  # write path
        await ctx.user_service.get_or_create(ctx.test_user_dto)  # read path (should be cached)
        await ctx.uow.rollback()

    assert await ctx.user_redis.get(ctx.user_redis_key) is None


async def test_user_services_get_or_create_when_register_dont_cache(
    user_test_context: UserTestContext,
):
    """Write path should not put data into Redis"""
    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.get_or_create(ctx.test_user_dto)
        await ctx.profile_service.get_or_create(ctx.test_user_dto.user_id)

    assert await ctx.user_redis.get(ctx.user_redis_key) is None
    assert await ctx.profile_redis.get(ctx.profile_redis_key) is None


async def test_user_services_get_or_create_cache_when_commit(user_test_context: UserTestContext):
    """Read path + commit data should be put into Redis"""
    ctx = user_test_context

    async with ctx.uow.transaction():
        await ctx.user_service.get_or_create(ctx.test_user_dto)  # write path
        await ctx.user_service.get_or_create(ctx.test_user_dto)  # read path (cache)

        await ctx.profile_service.get_or_create(ctx.test_user_dto.user_id)  # write path
        await ctx.profile_service.get_or_create(ctx.test_user_dto.user_id)  # read path (cache)

    cached_user = await ctx.user_redis.get(ctx.user_redis_key)
    cached_profile = await ctx.profile_redis.get(ctx.profile_redis_key)

    assert isinstance(cached_user, UserDTO)
    assert isinstance(cached_profile, UserProfileDTO)


async def test_register_or_update_usecase(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    aiogram_user: AiogramUser,
):
    ctx = user_test_context
    register_or_update = await request_container.get(UserRegisterOrUpdateUseCase)

    async with ctx.uow.transaction():
        result = await register_or_update.execute(aiogram_user)

    assert isinstance(result, RegisterResult)
    assert isinstance(result.user, UserDTO)
    assert isinstance(result.profile, UserProfileDTO)

    assert result.user.user_id == ctx.test_user_dto.user_id
    assert result.profile.user_id == ctx.test_user_dto.user_id


async def test_register_or_update_usecase_new_username(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    aiogram_user: AiogramUser,
):
    ctx = user_test_context
    register_or_update = await request_container.get(UserRegisterOrUpdateUseCase)

    new_username = "EternalGoonSesh"

    async with ctx.uow.transaction():
        initial_result = await register_or_update.execute(aiogram_user)

        updated_user = aiogram_user.model_copy(update={"username": new_username})
        updated_result = await register_or_update.execute(updated_user)

        get_user_dto = await ctx.user_service.get(ctx.test_user_dto.user_id)

    assert initial_result.user.username != updated_result.user.username
    assert updated_result.user.user_id == get_user_dto.user_id
    assert updated_result.user.username == new_username
    assert updated_result.user.username == get_user_dto.username
