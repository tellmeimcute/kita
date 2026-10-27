from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramUnauthorizedError
from sqlalchemy import select

from core.exceptions import (
    InvalidTokenError,
    TokenFromAnotherBotError,
    UserbotBanned,
    UserbotNotFoundError,
)
from database.models import UserBot

from ..scaffold import BOT_ID, BOT_TOKEN
from .conftest import ManagementContext

NEW_TOKEN = "123456789:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
FOREIGN_BOT_TOKEN = "111111:BBHdqTcvCH1vDDJxfSeofSAs0K5DALDsaw"


async def test_updates_token_and_refreshes_active_bot(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context

    await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

    stored = await ctx.userbot_service.get(BOT_ID)
    assert stored.token.get_secret_value() == NEW_TOKEN

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == NEW_TOKEN

    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)
    ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, NEW_TOKEN)
    ctx.set_webhook.assert_awaited_once_with(tg_bot)


async def test_inactive_userbot_skips_webhook(management_context: ManagementContext):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, active=False)

    await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

    stored = await ctx.userbot_service.get(BOT_ID)
    assert stored.token.get_secret_value() == NEW_TOKEN

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == NEW_TOKEN

    ctx.set_webhook.assert_not_awaited()
    ctx.bot_registry.remove.assert_not_called()


async def test_invalid_token_format(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(InvalidTokenError):
        await ctx.update_token.execute(ctx.owner, BOT_ID, "not-a-token")

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == BOT_TOKEN


async def test_token_from_another_bot(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(TokenFromAnotherBotError):
        await ctx.update_token.execute(ctx.owner, BOT_ID, FOREIGN_BOT_TOKEN)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == BOT_TOKEN
    ctx.bot_registry.remove.assert_not_called()


async def test_token_rejected_by_telegram(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context
    tg_bot.get_me = AsyncMock(
        side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
    )

    with pytest.raises(InvalidTokenError):
        await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == BOT_TOKEN
    ctx.bot_registry.remove.assert_not_called()


async def test_userbot_not_found(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.update_token.execute(ctx.owner, BOT_ID + 1, NEW_TOKEN)


async def test_banned_userbot(management_context: ManagementContext):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, banned=True)

    with pytest.raises(UserbotBanned):
        await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)


async def test_rejects_foreign_user(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.update_token.execute(ctx.stranger, BOT_ID, NEW_TOKEN)

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.token == BOT_TOKEN
