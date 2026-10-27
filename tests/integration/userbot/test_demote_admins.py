from collections.abc import Callable

import pytest

from core.exceptions import UserbotBanned, UserbotNotFoundError
from database.dto import UserDTO
from database.enums import UserRole

from ..scaffold import BOT_ID
from .conftest import ManagementContext


async def test_demotes_admins_except_owner(
    management_context: ManagementContext,
    user_dto_factory: Callable[..., UserDTO],
):
    ctx = management_context
    admins = [user_dto_factory() for _ in range(2)]
    regular = user_dto_factory()

    for user_dto in [*admins, regular]:
        async with ctx.uow.transaction():
            await ctx.user_repo.create(user_dto)
            await ctx.profile_service.create(user_dto.user_id)

    async with ctx.uow.transaction():
        for admin in admins:
            await ctx.profile_service.update(admin.user_id, role=UserRole.ADMIN)
        await ctx.profile_service.create(ctx.owner.user_id)
        await ctx.profile_service.update(ctx.owner.user_id, role=UserRole.ADMIN)

    # warm the per-user cache to make sure demotion invalidates it
    for user_dto in [*admins, regular, ctx.owner]:
        assert (await ctx.profile_service.get(user_dto.user_id)) is not None

    demoted = await ctx.demote_admins.execute(ctx.owner, BOT_ID)

    assert demoted == len(admins)

    owner_profile = await ctx.profile_service.get(ctx.owner.user_id)
    assert owner_profile.role == UserRole.ADMIN

    for admin in admins:
        profile = await ctx.profile_service.get(admin.user_id)
        assert profile.role == UserRole.USER

    assert (await ctx.profile_service.get(regular.user_id)).role == UserRole.USER


async def test_demotes_without_admins_returns_zero(management_context: ManagementContext):
    ctx = management_context

    assert await ctx.demote_admins.execute(ctx.owner, BOT_ID) == 0


async def test_userbot_not_found(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.demote_admins.execute(ctx.owner, BOT_ID + 1)


async def test_banned_userbot(management_context: ManagementContext):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, banned=True)

    with pytest.raises(UserbotBanned):
        await ctx.demote_admins.execute(ctx.owner, BOT_ID)


async def test_rejects_foreign_user(
    management_context: ManagementContext,
    user_dto_factory: Callable[..., UserDTO],
):
    ctx = management_context
    admin = user_dto_factory()
    async with ctx.uow.transaction():
        await ctx.user_repo.create(admin)
        await ctx.profile_service.create(admin.user_id)
        await ctx.profile_service.update(admin.user_id, role=UserRole.ADMIN)

    with pytest.raises(UserbotNotFoundError):
        await ctx.demote_admins.execute(ctx.stranger, BOT_ID)

    profile = await ctx.profile_service.get(admin.user_id)
    assert profile.role == UserRole.ADMIN
