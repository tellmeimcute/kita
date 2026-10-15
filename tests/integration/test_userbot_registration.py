from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import ChatFullInfo
from aiogram.types import User as AiogramUser
from dishka import AsyncContainer
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.cryptographer import Cryptographer
from core.exceptions import (
    BadRequestError,
    ChannelNotFoundError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    UserbotAlreadyExistsError,
)
from database.dto import UserBotDTO, UserDTO
from database.models import UserAlchemy, UserBot, UserProfile
from database.repository import UserRepository
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserBotRepositoryProtocol
from services import UserBotService
from usecases import UserBotRegisterUseCase

BOT_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
BOT_ID = 123456789
BOT_USERNAME = "test_userbot"
CHANNEL_ID = -100123456789
CHANNEL_NAME = "Test Channel"
CHANNEL_INPUT = "123456789"


@dataclass(frozen=True)
class UserBotTestContext:
    uow: UnitOfWorkProtocol
    register: UserBotRegisterUseCase
    userbot_service: UserBotService
    userbot_repo: UserBotRepositoryProtocol
    crypto: Cryptographer
    bot_registry: BotRegistryProtocol
    owner_id: int


@pytest.fixture
def tg_channel() -> MagicMock:
    channel = MagicMock(spec=ChatFullInfo)
    channel.id = CHANNEL_ID
    channel.full_name = CHANNEL_NAME
    channel.type = "channel"
    return channel


@pytest.fixture
def tg_bot(tg_channel: MagicMock) -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.id = BOT_ID
    bot.token = BOT_TOKEN
    bot.__aenter__ = AsyncMock(return_value=bot)
    bot.__aexit__ = AsyncMock(return_value=False)

    bot.get_me = AsyncMock(
        return_value=AiogramUser(id=BOT_ID, is_bot=True, first_name="Test", username=BOT_USERNAME)
    )
    bot.get_chat = AsyncMock(return_value=tg_channel)
    bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=True)
    )

    return bot


@pytest.fixture
def patched_bot(tg_bot: MagicMock) -> Iterator[MagicMock]:
    with patch("usecases.ub_register.Bot") as bot_cls:
        bot_cls.return_value = tg_bot
        yield bot_cls


@pytest.fixture
async def userbot_test_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
) -> AsyncIterator[UserBotTestContext]:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo = await request_container.get(UserRepository)
    bot_registry = await request_container.get(BotRegistryProtocol)
    session = await request_container.get(AsyncSession)

    bot_registry.bot_settings = {}
    bot_registry.remove.reset_mock()
    bot_registry.get_or_create.reset_mock()

    owner_dto = user_dto_factory()
    async with uow.transaction():
        await user_repo.create(owner_dto)

    ctx = UserBotTestContext(
        uow=uow,
        register=await request_container.get(UserBotRegisterUseCase),
        userbot_service=await request_container.get(UserBotService),
        userbot_repo=await request_container.get(UserBotRepositoryProtocol),
        crypto=await request_container.get(Cryptographer),
        bot_registry=bot_registry,
        owner_id=owner_dto.user_id,
    )

    yield ctx

    await session.execute(delete(UserBot).where(UserBot.owner_id == ctx.owner_id))
    await session.execute(delete(UserProfile).where(UserProfile.user_id == ctx.owner_id))
    await session.execute(delete(UserAlchemy).where(UserAlchemy.user_id == ctx.owner_id))
    await session.commit()


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
    patched_bot: MagicMock,
    tg_bot: MagicMock,
    channel_input: str,
    expected_chat_arg: int | str,
):
    ctx = userbot_test_context
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    bot_info = await ctx.register.execute(raw_token, channel_input, owner_id=ctx.owner_id)

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
    patched_bot: MagicMock,
):
    ctx = userbot_test_context
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)
    ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, BOT_TOKEN)


async def test_register_userbot_already_exists(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
):
    ctx = userbot_test_context
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    with pytest.raises(UserbotAlreadyExistsError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    ctx.bot_registry.remove.assert_called_once_with(BOT_ID)


async def test_register_userbot_without_token(userbot_test_context: UserBotTestContext):
    ctx = userbot_test_context

    with pytest.raises(BadRequestError):
        await ctx.register.execute(None, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_without_channel(userbot_test_context: UserBotTestContext):
    ctx = userbot_test_context
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(BadRequestError):
        await ctx.register.execute(raw_token, None, owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_invalid_channel_id(
    userbot_test_context: UserBotTestContext,
):
    ctx = userbot_test_context
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(ChannelNotFoundError):
        await ctx.register.execute(raw_token, "not-a-channel", owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_not_a_channel(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
    tg_channel: MagicMock,
):
    ctx = userbot_test_context
    tg_channel.type = "group"
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(NotAChannelError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_insufficient_permissions(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=False)
    )
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(InsufficientPermissionsError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_not_admin_member(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat_member = AsyncMock(return_value=MagicMock(status=ChatMemberStatus.MEMBER))
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(InsufficientPermissionsError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_chat_not_found(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_chat = AsyncMock(
        side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
    )
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(BadRequestError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

    assert await ctx.userbot_repo.get(BOT_ID) is None


async def test_register_userbot_invalid_token(
    userbot_test_context: UserBotTestContext,
    patched_bot: MagicMock,
    tg_bot: MagicMock,
):
    ctx = userbot_test_context
    tg_bot.get_me = AsyncMock(
        side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
    )
    raw_token = ctx.crypto.encrypt(BOT_TOKEN)

    with pytest.raises(InvalidTokenError):
        await ctx.register.execute(raw_token, str(CHANNEL_ID), owner_id=ctx.owner_id)

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
        stored = await ctx.userbot_repo.get(BOT_ID)
        await ctx.uow.rollback()

    assert isinstance(stored, UserBotDTO)
    assert stored.bot_id == BOT_ID
    assert stored.token.get_secret_value() == BOT_TOKEN
    assert stored.owner_id == ctx.owner_id
