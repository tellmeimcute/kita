import pytest
from sqlalchemy.exc import IntegrityError

from database.dto import UserDTO

from .conftest import RepositoryContext


async def test_get_nonexistent(repository_context: RepositoryContext):
    ctx = repository_context

    user_dto = await ctx.user_repo.get_by_id(7313)

    assert user_dto is None


async def test_get_existed(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        await ctx.user_repo.create(ctx.test_user_dto)
        user_dto = await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == ctx.test_user_dto.user_id


async def test_create(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        user_dto = await ctx.user_repo.create(ctx.test_user_dto)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == ctx.test_user_dto.user_id


async def test_create_existed(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        await ctx.user_repo.create(ctx.test_user_dto)

        with pytest.raises(IntegrityError):
            await ctx.user_repo.create(ctx.test_user_dto)
            
        await ctx.uow.rollback()

    assert await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id) is None


async def test_get_or_create(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        user_dto = await ctx.user_repo.get_or_create(ctx.test_user_dto)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == ctx.test_user_dto.user_id


async def test_get_or_create_2times(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        first = await ctx.user_repo.get_or_create(ctx.test_user_dto)
        two = await ctx.user_repo.get_or_create(ctx.test_user_dto)

    assert isinstance(first, UserDTO)
    assert isinstance(two, UserDTO)

    assert first.user_id == ctx.test_user_dto.user_id
    assert two.user_id == ctx.test_user_dto.user_id

    assert first.created_at == two.created_at


async def test_update(repository_context: RepositoryContext):
    ctx = repository_context

    new_username = "LOSHARA"

    async with ctx.uow.transaction():
        newly_created = await ctx.user_repo.create(ctx.test_user_dto)

        await ctx.user_repo.update(ctx.test_user_dto.user_id, username=new_username)
        updated = await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id)

    assert newly_created.user_id == updated.user_id
    assert newly_created.username != updated.username
    assert updated.username == new_username
