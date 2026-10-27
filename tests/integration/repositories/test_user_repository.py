import pytest
from sqlalchemy.exc import IntegrityError

from database.dto import UserDTO

from ..readers import load_user
from .conftest import RepositoryContext

OTHER_USER_ID_OFFSET = 1_000


def make_other_user(ctx: RepositoryContext) -> UserDTO:
    return ctx.test_user_dto.model_copy(
        update={
            "user_id": ctx.test_user_dto.user_id + OTHER_USER_ID_OFFSET,
            "username": f"{ctx.test_user_dto.username}_other",
        }
    )


async def test_get_nonexistent(repository_context: RepositoryContext):
    ctx = repository_context

    user_dto = await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id + 1)

    assert user_dto is None


async def test_get_existed(repository_context: RepositoryContext):
    ctx = repository_context

    user_dto = await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id)

    assert isinstance(user_dto, UserDTO)
    assert user_dto.user_id == ctx.test_user_dto.user_id
    assert user_dto.username == ctx.test_user_dto.username


async def test_create(repository_context: RepositoryContext):
    ctx = repository_context
    other_user = make_other_user(ctx)

    async with ctx.uow.transaction():
        created = await ctx.user_repo.create(other_user)

    assert isinstance(created, UserDTO)
    assert created.user_id == other_user.user_id
    assert created.username == other_user.username


async def test_create_existed(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        with pytest.raises(IntegrityError):
            await ctx.user_repo.create(ctx.test_user_dto)
            
        await ctx.uow.rollback()

    assert await ctx.user_repo.get_by_id(ctx.test_user_dto.user_id) is not None


async def test_get_or_create(repository_context: RepositoryContext):
    ctx = repository_context
    other_user = make_other_user(ctx)

    async with ctx.uow.transaction():
        created = await ctx.user_repo.get_or_create(other_user)

    assert isinstance(created, UserDTO)
    assert created.user_id == other_user.user_id
    assert created.username == other_user.username


async def test_get_or_create_2times(repository_context: RepositoryContext):
    ctx = repository_context
    other_user = make_other_user(ctx)

    async with ctx.uow.transaction():
        first = await ctx.user_repo.get_or_create(other_user)
        two = await ctx.user_repo.get_or_create(other_user)

    assert first.user_id == two.user_id == other_user.user_id
    assert first.created_at == two.created_at


async def test_update(repository_context: RepositoryContext):
    ctx = repository_context

    new_username = "LOSHARA"

    async with ctx.uow.transaction():
        await ctx.user_repo.update(ctx.test_user_dto.user_id, username=new_username)

    updated = await load_user(ctx, ctx.test_user_dto.user_id)

    assert updated.username == new_username
    assert updated.username != ctx.test_user_dto.username
