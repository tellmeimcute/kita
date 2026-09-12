from collections.abc import Callable

from dishka import AsyncContainer

from database.dto import UserDTO, UserProfileDTO
from interfaces import UnitOfWorkProtocol, UserProfileServiceProtocol, UserServiceProtocol


async def test_register_user(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
):
    """TEST USER MIDDLEWARE CASE"""

    uow = await request_container.get(UnitOfWorkProtocol)
    user_service = await request_container.get(UserServiceProtocol)
    user_profile_service = await request_container.get(UserProfileServiceProtocol)

    test_user_dto = user_dto_factory()

    async with uow.transaction():
        user_dto = await user_service.get_or_create(test_user_dto)
        profile_dto = await user_profile_service.get_or_create(test_user_dto.user_id)
        await uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert isinstance(profile_dto, UserProfileDTO)

    assert user_dto.user_id == profile_dto.user_id


async def test_redis_stalling_data(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
):
    uow = await request_container.get(UnitOfWorkProtocol)
    user_service = await request_container.get(UserServiceProtocol)

    test_user_dto = user_dto_factory()

    async with uow.transaction():
        await user_service.create(test_user_dto)
        await uow.rollback()

    async with uow.transaction():
        user_dto = await user_service.get(test_user_dto.user_id)
        await uow.rollback()

    assert user_dto is None
