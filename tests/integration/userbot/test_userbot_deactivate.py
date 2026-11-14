from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from core.exceptions import UserbotBanned, UserbotNotFoundError
from database.models import UserBot
from events import UserbotDeactivated

from ..scaffold import BOT_ID
from .conftest import ManagementContext


async def test_active_userbot_becomes_inactive(
    management_context: ManagementContext,
    tg_bot: MagicMock,
    event_recorder,
):
    ctx = management_context

    result = await ctx.deactivate.execute(ctx.owner, BOT_ID)

    assert result.active is False
    assert (await ctx.userbot_service.get(BOT_ID)).active is False
    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is False

    tg_bot.get_me.assert_not_awaited()
    tg_bot.get_chat.assert_not_awaited()

    ctx.remove_webhook.assert_awaited_once_with(tg_bot)
    ctx.set_webhook.assert_not_awaited()
    assert ctx.cache.get(BOT_ID) is None
    assert (
        UserbotDeactivated(bot_id=BOT_ID, userbot_id=BOT_ID, owner_id=ctx.owner.user_id)
        in event_recorder.events
    )


async def test_inactive_userbot_is_left_untouched(
    management_context: ManagementContext,
    event_recorder,
):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, active=False)

    result = await ctx.deactivate.execute(ctx.owner, BOT_ID)

    assert result.active is False
    ctx.remove_webhook.assert_not_awaited()
    ctx.set_webhook.assert_not_awaited()
    assert event_recorder.events == []


async def test_rejects_foreign_user(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.deactivate.execute(ctx.stranger, BOT_ID)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is True
    ctx.set_webhook.assert_not_awaited()
    ctx.remove_webhook.assert_not_awaited()


async def test_banned_userbot(management_context: ManagementContext):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, banned=True)

    with pytest.raises(UserbotBanned):
        await ctx.deactivate.execute(ctx.owner, BOT_ID)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is True
    ctx.set_webhook.assert_not_awaited()
    ctx.remove_webhook.assert_not_awaited()


async def test_userbot_not_found(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.deactivate.execute(ctx.owner, BOT_ID + 1)
