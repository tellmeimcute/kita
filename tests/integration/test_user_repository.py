import pytest
from dishka import AsyncContainer
from sqlalchemy.exc import IntegrityError

from database.dto import UserDTO
from database.repository import UserRepository
from interfaces import UnitOfWorkProtocol


async def test_get_nonexistent(request_container: AsyncContainer):
    user_repository = await request_container.get(UserRepository)

    user_dto = await user_repository.get_by_id(7313)

    assert user_dto is None


async def test_get_existed(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        await user_repository.create(test_user_dto)
        user_dto = await user_repository.get_by_id(test_user_dto.user_id)
        await uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id


async def test_create(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        user_dto = await user_repository.create(test_user_dto)
        await uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id


async def test_create_existed(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        await user_repository.create(test_user_dto)

        with pytest.raises(IntegrityError):
            await user_repository.create(test_user_dto)
        await uow.rollback()


async def test_get_or_create(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        user_dto = await user_repository.get_or_create(test_user_dto)
        await uow.rollback()

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id


async def test_get_or_create_2times(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        first = await user_repository.get_or_create(test_user_dto)
        two = await user_repository.get_or_create(test_user_dto)
        await uow.rollback()

    assert isinstance(first, UserDTO)
    assert isinstance(two, UserDTO)

    assert first.user_id == test_user_dto.user_id
    assert two.user_id == test_user_dto.user_id

    assert first.created_at == two.created_at


async def test_update(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    uow = await request_container.get(UnitOfWorkProtocol)

    new_username = "LOSHARA"

    async with uow.transaction():
        newly_created = await user_repository.create(test_user_dto)

        await user_repository.update(test_user_dto.user_id, username=new_username)
        updated = await user_repository.get_by_id(test_user_dto.user_id)
        await uow.rollback()

    assert newly_created.user_id == updated.user_id
    assert newly_created.username != updated.username
    assert updated.username == new_username
