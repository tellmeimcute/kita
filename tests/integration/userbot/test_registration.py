from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError

from core.exceptions import (
    BadRequestError,
    ChannelNotFoundError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    UserbotAlreadyExistsError,
)
from database.dto import UserBotDTO

from ..scaffold import (
    BOT_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    CHANNEL_ID,
    CHANNEL_INPUT,
    CHANNEL_NAME,
)
from .conftest import UserBotTestContext


@pytest.mark.parametrize(
    ("channel_input", "expected_chat_arg"),
    [
        (CHANNEL_INPUT, CHANNEL_ID),
        (str(CHANNEL_ID), CHANNEL_ID),
        ("@testchannel", "@testchannel"),
    ],
)
async def test_register_userbot_creates_record(
    userbot_test_context: UserBotTestContext,
    tg_bot: MagicMock,
    channel_input: str,
    expected_chat_arg: int | str,
):
    ctx = userbot_test_context

    bot_info = await ctx.register.execute(ctx.raw_token, channel_input, owner_id=ctx.owner_id)

    assert bot_info.id == BOT_ID
    tg_bot.get_chat.assert_awaited_once_with(expected_chat_arg)

    stored = await ctx.userbot_service.get(BOT_ID)

    assert isinstance(stored, UserBotDTO)
    assert stored.bot_id == BOT_ID
    assert stored.username == BOT_USERNAME
    assert stored.owner_id == ctx.owner_id
    assert stored.channel_id == CHANNEL_ID
    assert stored.channel_name == CHANNEL_NAME
    assert stored.token.get_secret_value() == BOT_TOKEN
    assert stored.active is True
    assert stored.banned is False


async def test_register_userbot_registers_bot_in_registry(
    userbot_test_context: UserBotTestContext,
):
    ctx = userbot_test_context

    await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)
    ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, BOT_TOKEN)


async def test_register_userbot_already_exists(
    userbot_test_context: UserBotTestContext,
):
    ctx = userbot_test_context

    await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    with pytest.raises(UserbotAlreadyExistsError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)


async def test_register_userbot_without_token(userbot_test_context: UserBotTestContext):
    ctx = userbot_test_context

    with pytest.raises(BadRequestError):
        await ctx.register.execute(None, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_without_channel(userbot_test_context: UserBotTestContext):
    ctx = userbot_test_context

    with pytest.raises(BadRequestError):
        await ctx.register.execute(ctx.raw_token, None, owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_invalid_channel_id(
    userbot_test_context: UserBotTestContext,
):
    ctx = userbot_test_context

    with pytest.raises(ChannelNotFoundError):
        await ctx.register.execute(ctx.raw_token, "not-a-channel", owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_not_a_channel(
    userbot_test_context: UserBotTestContext,
    tg_channel: MagicMock,
):
    ctx = userbot_test_context
    tg_channel.type = "group"

    with pytest.raises(NotAChannelError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_insufficient_permissions(
    userbot_test_context: UserBotTestContext,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=False)
    )

    with pytest.raises(InsufficientPermissionsError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_not_admin_member(
    userbot_test_context: UserBotTestContext,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat_member = AsyncMock(return_value=MagicMock(status=ChatMemberStatus.MEMBER))

    with pytest.raises(InsufficientPermissionsError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_chat_not_found(
    userbot_test_context: UserBotTestContext,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat = AsyncMock(
        side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
    )

    with pytest.raises(BadRequestError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_invalid_token(
    userbot_test_context: UserBotTestContext,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_me = AsyncMock(
        side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
    )

    with pytest.raises(InvalidTokenError):
        await ctx.register.execute(ctx.raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_userbot_service_create_persists(userbot_test_context: UserBotTestContext):
    ctx = userbot_test_context

    async with ctx.uow.transaction():
        await ctx.userbot_service.create(
            token=BOT_TOKEN,
            bot_id=BOT_ID,
            username=BOT_USERNAME,
            owner_id=ctx.owner_id,
            channel_id=CHANNEL_ID,
            channel_name=CHANNEL_NAME,
        )

    async with ctx.uow.transaction():
        stored = await ctx.userbot_repo.get(BOT_ID)

    assert isinstance(stored, UserBotDTO)
    assert stored.bot_id == BOT_ID
    assert stored.token.get_secret_value() == BOT_TOKEN
    assert stored.owner_id == ctx.owner_id
