from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus
from sqlalchemy import select

from core.exceptions import (
    ChannelNotFoundError,
    InsufficientPermissionsError,
    NotAChannelError,
    UserbotBanned,
    UserbotNotFoundError,
)
from database.models import UserBot

from ..scaffold import BOT_ID, BOT_TOKEN, CHANNEL_ID, CHANNEL_NAME
from .conftest import ManagementContext

NEW_CHANNEL_ID = -100987654321
NEW_CHANNEL_NAME = "New Channel"


async def test_updates_channel(
    management_context: ManagementContext,
    tg_bot: MagicMock,
    tg_channel: MagicMock,
):
    ctx = management_context
    tg_channel.id = NEW_CHANNEL_ID
    tg_channel.full_name = NEW_CHANNEL_NAME

    result = await ctx.update_channel.execute(ctx.owner, BOT_ID, "987654321")

    assert result.channel_id == NEW_CHANNEL_ID
    assert result.channel_name == NEW_CHANNEL_NAME

    stored = await ctx.userbot_service.get(BOT_ID)
    assert stored.channel_id == NEW_CHANNEL_ID
    assert stored.channel_name == NEW_CHANNEL_NAME

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == NEW_CHANNEL_ID
    assert row.channel_name == NEW_CHANNEL_NAME

    ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, BOT_TOKEN)
    tg_bot.get_chat.assert_awaited_once_with(NEW_CHANNEL_ID)


async def test_invalid_channel_input(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(ChannelNotFoundError):
        await ctx.update_channel.execute(ctx.owner, BOT_ID, "not-a-channel")

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == CHANNEL_ID


async def test_probe_rejects_non_channel(
    management_context: ManagementContext,
    tg_channel: MagicMock,
):
    ctx = management_context
    tg_channel.type = "group"

    with pytest.raises(NotAChannelError):
        await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == CHANNEL_ID


async def test_probe_rejects_insufficient_permissions(
    management_context: ManagementContext,
    tg_bot: MagicMock,
    tg_channel: MagicMock,
):
    ctx = management_context
    tg_channel.id = NEW_CHANNEL_ID
    tg_channel.full_name = NEW_CHANNEL_NAME
    tg_bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=False)
    )

    with pytest.raises(InsufficientPermissionsError):
        await ctx.update_channel.execute(ctx.owner, BOT_ID, "987654321")

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == CHANNEL_ID
    assert row.channel_name == CHANNEL_NAME


async def test_probe_rejects_non_admin_member(
    management_context: ManagementContext,
    tg_bot: MagicMock,
):
    ctx = management_context
    tg_bot.get_chat_member = AsyncMock(return_value=MagicMock(status=ChatMemberStatus.MEMBER))

    with pytest.raises(InsufficientPermissionsError):
        await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == CHANNEL_ID
    assert row.channel_name == CHANNEL_NAME


async def test_userbot_not_found(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.update_channel.execute(ctx.owner, BOT_ID + 1, str(CHANNEL_ID))


async def test_banned_userbot(management_context: ManagementContext):
    ctx = management_context
    async with ctx.uow.transaction():
        await ctx.userbot_service.update(BOT_ID, banned=True)

    with pytest.raises(UserbotBanned):
        await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))


async def test_rejects_foreign_user(management_context: ManagementContext):
    ctx = management_context

    with pytest.raises(UserbotNotFoundError):
        await ctx.update_channel.execute(ctx.stranger, BOT_ID, "987654321")

    async with ctx.session_maker() as session:
        row = await session.scalar(select(UserBot).where(UserBot.bot_id == BOT_ID))
    assert row.channel_id == CHANNEL_ID
    assert row.channel_name == CHANNEL_NAME
