import pytest
from sqlalchemy.exc import IntegrityError
from dishka import AsyncContainer

from database.dto import UserDTO
from database.repository import UserRepository

async def test_get_nonexistent(request_container: AsyncContainer):
    user_repository = await request_container.get(UserRepository)

    user_dto = await user_repository.get_by_id(7313)

    assert user_dto is None

async def test_get_existed(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)

    await user_repository.create(test_user_dto)
    
    user_dto = await user_repository.get_by_id(test_user_dto.user_id)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id

async def test_create(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)

    user_dto = await user_repository.create(test_user_dto)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id

async def test_create_existed(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)

    await user_repository.create(test_user_dto)

    with pytest.raises(IntegrityError):
        await user_repository.create(test_user_dto)

async def test_get_or_create(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)

    user_dto = await user_repository.get_or_create(test_user_dto)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == test_user_dto.user_id

async def test_get_or_create_2times(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)
    
    user_dto_first = await user_repository.get_or_create(test_user_dto)
    user_dto_two = await user_repository.get_or_create(test_user_dto)

    assert isinstance(user_dto_first, UserDTO)
    assert isinstance(user_dto_two, UserDTO)

    assert user_dto_first.user_id == test_user_dto.user_id
    assert user_dto_two.user_id == test_user_dto.user_id

    assert user_dto_first.created_at == user_dto_two.created_at

async def test_update(request_container: AsyncContainer, test_user_dto: UserDTO):
    user_repository = await request_container.get(UserRepository)

    new_username = "LOSHARA"
    newly_created = await user_repository.create(test_user_dto)

    await user_repository.update(test_user_dto.user_id, username=new_username)
    updated = await user_repository.get_by_id(test_user_dto.user_id)

    assert newly_created.user_id == updated.user_id
    assert newly_created.username != updated.username
    assert updated.username == new_username