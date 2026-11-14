from ..scaffold import BOT_ID
from .conftest import RepositoryContext


async def test_deactivate_switches_the_flag_off(repository_context: RepositoryContext):
    ctx = repository_context

    deactivated = await ctx.userbot_repo.deactivate(BOT_ID)

    assert deactivated is not None
    assert deactivated.active is False
    assert (await ctx.userbot_repo.get(BOT_ID)).active is False


async def test_deactivate_leaves_inactive_bot_untouched(repository_context: RepositoryContext):
    ctx = repository_context
    async with ctx.uow.transaction():
        await ctx.userbot_repo.update(BOT_ID, active=False)

    assert await ctx.userbot_repo.deactivate(BOT_ID) is None
    assert (await ctx.userbot_repo.get(BOT_ID)).active is False


async def test_deactivate_of_missing_bot(repository_context: RepositoryContext):
    ctx = repository_context

    assert await ctx.userbot_repo.deactivate(BOT_ID + 1) is None


async def test_activate_switches_the_flag_on(repository_context: RepositoryContext):
    ctx = repository_context
    async with ctx.uow.transaction():
        await ctx.userbot_repo.update(BOT_ID, active=False)

    activated = await ctx.userbot_repo.activate(BOT_ID)

    assert activated is not None
    assert activated.active is True
    assert (await ctx.userbot_repo.get(BOT_ID)).active is True


async def test_activate_leaves_active_bot_untouched(repository_context: RepositoryContext):
    ctx = repository_context

    assert await ctx.userbot_repo.activate(BOT_ID) is None
    assert (await ctx.userbot_repo.get(BOT_ID)).active is True


async def test_activate_leaves_banned_bot_untouched(repository_context: RepositoryContext):
    ctx = repository_context
    async with ctx.uow.transaction():
        await ctx.userbot_repo.update(BOT_ID, active=False, banned=True)

    assert await ctx.userbot_repo.activate(BOT_ID) is None
    assert (await ctx.userbot_repo.get(BOT_ID)).active is False


async def test_activate_of_missing_bot(repository_context: RepositoryContext):
    ctx = repository_context

    assert await ctx.userbot_repo.activate(BOT_ID + 1) is None
