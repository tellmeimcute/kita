from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from sqlalchemy import select

from core.exceptions import (
    BadRequestError,
    InvalidTokenError,
    UserbotBanned,
    UserbotNotFoundError,
)
from database.models import UserBot

from ..scaffold import BOT_ID
from .conftest import ManagementContext


async def test_active_userbot_becomes_inactive(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context

    result = await ctx.active_toggle.execute(ctx.owner, BOT_ID)

    assert result.active is False
    assert (await ctx.userbot_service.get(BOT_ID)).active is False
    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is False

    ctx.remove_webhook.assert_awaited_once_with(tg_bot)
    ctx.set_webhook.assert_not_awaited()
    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)


async def test_inactive_userbot_becomes_active(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, active=False)

    result = await ctx.active_toggle.execute(ctx.owner, BOT_ID)

    assert result.active is True
    assert (await ctx.userbot_service.get(BOT_ID)).active is True
    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is True

    ctx.set_webhook.assert_awaited_once_with(tg_bot)
    ctx.remove_webhook.assert_not_awaited()
    ctx.bot_registry.remove.assert_not_called()


async def test_probe_failure_deactivates_userbot(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context
    tg_bot.get_chat = AsyncMock(
        side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
    )

    with pytest.raises(BadRequestError):
        await ctx.active_toggle.execute(ctx.owner, BOT_ID)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is False
    ctx.remove_webhook.assert_awaited_once_with(tg_bot)
    ctx.set_webhook.assert_not_awaited()
    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)


async def test_invalid_token_deactivates_without_webhook_removal(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context
    tg_bot.get_me = AsyncMock(
        side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
    )

    with pytest.raises(InvalidTokenError):
        await ctx.active_toggle.execute(ctx.owner, BOT_ID)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is False
    ctx.remove_webhook.assert_not_awaited()
    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)


async def test_rejects_foreign_user(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.active_toggle.execute(ctx.stranger, BOT_ID)

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
        await ctx.active_toggle.execute(ctx.owner, BOT_ID)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.active is True
    ctx.set_webhook.assert_not_awaited()
    ctx.remove_webhook.assert_not_awaited()


async def test_userbot_not_found(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.active_toggle.execute(ctx.owner, BOT_ID + 1)
