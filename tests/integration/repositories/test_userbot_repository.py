from ..scaffold import BOT_ID
from .conftest import RepositoryContext


async def test_toggle_active_flips_the_flag(repository_context: RepositoryContext):
    ctx = repository_context

    toggled = await ctx.userbot_repo.toggle_active(BOT_ID)

    assert toggled is not None
    assert toggled.active is False
    assert (await ctx.userbot_repo.get(BOT_ID)).active is False

    toggled = await ctx.userbot_repo.toggle_active(BOT_ID)

    assert toggled is not None
    assert toggled.active is True
    assert (await ctx.userbot_repo.get(BOT_ID)).active is True


async def test_toggle_active_leaves_banned_bot_untouched(repository_context: RepositoryContext):
    ctx = repository_context
    async with ctx.uow.transaction():
        await ctx.userbot_repo.update(BOT_ID, banned=True)

    assert await ctx.userbot_repo.toggle_active(BOT_ID) is None
    assert (await ctx.userbot_repo.get(BOT_ID)).active is True


async def test_toggle_active_of_missing_bot(repository_context: RepositoryContext):
    ctx = repository_context

    assert await ctx.userbot_repo.toggle_active(BOT_ID + 1) is None
