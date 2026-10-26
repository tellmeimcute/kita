from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
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

from core.exceptions import (
    BadRequestError,
    ChannelNotFoundError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    TokenFromAnotherBotError,
    UserbotBanned,
    UserbotNotFoundError,
)
from database.dto import UserDTO
from database.enums import UserRole
from database.models import UserAlchemy, UserBot, UserProfile
from database.repository import UserRepository
from interfaces import (
    BotRegistryProtocol,
    UnitOfWorkProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
    WebhookServiceProtocol,
)
from services import UserBotService
from usecases import (
    UserbotActiveToggleUseCase,
    UserbotDemoteAdminsUseCase,
    UserbotUpdateChannelUseCase,
    UserbotUpdateTokenUseCase,
)

BOT_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
BOT_ID = 123456789
BOT_USERNAME = "test_userbot"

CHANNEL_ID = -100123456789
CHANNEL_NAME = "Test Channel"

NEW_TOKEN = "123456789:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
FOREIGN_BOT_TOKEN = "111111:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
NEW_CHANNEL_ID = -100987654321
NEW_CHANNEL_NAME = "New Channel"


@dataclass(frozen=True)
class ManagementContext:
    uow: UnitOfWorkProtocol
    update_token: UserbotUpdateTokenUseCase
    update_channel: UserbotUpdateChannelUseCase
    demote_admins: UserbotDemoteAdminsUseCase
    active_toggle: UserbotActiveToggleUseCase
    userbot_service: UserBotServiceProtocol
    user_repo: UserRepository
    profile_service: UserProfileServiceProtocol
    set_webhook: AsyncMock
    remove_webhook: AsyncMock
    bot_registry: BotRegistryProtocol
    owner: UserDTO
    stranger: UserDTO
    created_user_ids: list[int] = field(default_factory=list)


class _BotContext:
    def __init__(self, registry: BotRegistryProtocol, bot: MagicMock):
        self._registry = registry
        self._bot = bot
        self._prev = None

    async def __aenter__(self) -> MagicMock:
        self._prev = self._registry.get_current.return_value
        self._registry.get_current.return_value = self._bot
        return self._bot

    async def __aexit__(self, *exc_info) -> bool:
        self._registry.get_current.return_value = self._prev
        return False


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
def patched_probe_bot(tg_bot: MagicMock) -> Iterator[MagicMock]:
    with patch("utils.userbot_probe.Bot", MagicMock(return_value=tg_bot)):
        yield tg_bot


@pytest.fixture
async def management_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
    tg_bot: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[ManagementContext]:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo = await request_container.get(UserRepository)
    userbot_service = await request_container.get(UserBotServiceProtocol)
    profile_service = await request_container.get(UserProfileServiceProtocol)
    bot_registry = await request_container.get(BotRegistryProtocol)
    webhook_service = await request_container.get(WebhookServiceProtocol)
    session = await request_container.get(AsyncSession)

    bot_registry.tmp_bot_settings = {}
    monkeypatch.setattr(bot_registry, "get_current", MagicMock(return_value=tg_bot))
    monkeypatch.setattr(bot_registry, "remove", MagicMock())
    monkeypatch.setattr(bot_registry, "get_or_create", MagicMock(return_value=tg_bot))
    monkeypatch.setattr(
        bot_registry,
        "with_bot",
        lambda bot, *args, **kwargs: _BotContext(bot_registry, bot),
    )

    set_webhook = AsyncMock()
    remove_webhook = AsyncMock()
    monkeypatch.setattr(webhook_service, "set_webhook", set_webhook)
    monkeypatch.setattr(webhook_service, "remove_webhook", remove_webhook)

    owner = user_dto_factory()
    stranger = user_dto_factory()
    async with uow.transaction():
        await user_repo.create(owner)
        await user_repo.create(stranger)

    async with uow.transaction():
        await userbot_service.create(
            token=BOT_TOKEN,
            bot_id=BOT_ID,
            username=BOT_USERNAME,
            owner_id=owner.user_id,
            channel_id=CHANNEL_ID,
            channel_name=CHANNEL_NAME,
        )

    ctx = ManagementContext(
        uow=uow,
        update_token=await request_container.get(UserbotUpdateTokenUseCase),
        update_channel=await request_container.get(UserbotUpdateChannelUseCase),
        demote_admins=await request_container.get(UserbotDemoteAdminsUseCase),
        active_toggle=await request_container.get(UserbotActiveToggleUseCase),
        userbot_service=userbot_service,
        user_repo=user_repo,
        profile_service=profile_service,
        set_webhook=set_webhook,
        remove_webhook=remove_webhook,
        bot_registry=bot_registry,
        owner=owner,
        stranger=stranger,
        created_user_ids=[owner.user_id, stranger.user_id],
    )

    yield ctx

    await session.execute(delete(UserBot).where(UserBot.owner_id == owner.user_id))
    await session.execute(delete(UserProfile).where(UserProfile.bot_id == BOT_ID))
    await session.execute(delete(UserProfile).where(UserProfile.user_id.in_(ctx.created_user_ids)))
    await session.execute(delete(UserAlchemy).where(UserAlchemy.user_id.in_(ctx.created_user_ids)))
    await session.commit()


@pytest.fixture
async def userbot_save_spy(
    management_context: ManagementContext,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncMock:
    spy = AsyncMock(wraps=management_context.userbot_service.save)
    monkeypatch.setattr(UserBotService, "save", spy)
    return spy


class TestUpdateToken:
    async def test_updates_token_and_refreshes_active_bot(
        self,
        management_context: ManagementContext,
        patched_probe_bot: MagicMock,
        userbot_save_spy: AsyncMock,
    ):
        ctx = management_context

        await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == NEW_TOKEN

        userbot_save_spy.assert_awaited_once()
        ctx.bot_registry.remove.assert_called_once_with(BOT_ID)
        ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, NEW_TOKEN)
        ctx.set_webhook.assert_awaited_once_with(patched_probe_bot)

    async def test_inactive_userbot_skips_webhook(
        self, management_context: ManagementContext, patched_probe_bot: MagicMock
    ):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, active=False)

        await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == NEW_TOKEN
        ctx.set_webhook.assert_not_awaited()
        ctx.bot_registry.remove.assert_not_called()

    async def test_invalid_token_format(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(InvalidTokenError):
            await ctx.update_token.execute(ctx.owner, BOT_ID, "not-a-token")

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == BOT_TOKEN

    async def test_token_from_another_bot(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(TokenFromAnotherBotError):
            await ctx.update_token.execute(ctx.owner, BOT_ID, FOREIGN_BOT_TOKEN)

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == BOT_TOKEN
        ctx.bot_registry.remove.assert_not_called()

    async def test_token_rejected_by_telegram(
        self,
        management_context: ManagementContext,
        patched_probe_bot: MagicMock,
        tg_bot: MagicMock,
    ):
        ctx = management_context
        tg_bot.get_me = AsyncMock(
            side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
        )

        with pytest.raises(InvalidTokenError):
            await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == BOT_TOKEN
        ctx.bot_registry.remove.assert_not_called()

    async def test_userbot_not_found(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.update_token.execute(ctx.owner, BOT_ID + 1, NEW_TOKEN)

    async def test_banned_userbot(self, management_context: ManagementContext):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, banned=True)

        with pytest.raises(UserbotBanned):
            await ctx.update_token.execute(ctx.owner, BOT_ID, NEW_TOKEN)

    async def test_rejects_foreign_user(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.update_token.execute(ctx.stranger, BOT_ID, NEW_TOKEN)

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.token.get_secret_value() == BOT_TOKEN


class TestUpdateChannel:
    async def test_updates_channel(
        self,
        management_context: ManagementContext,
        tg_bot: MagicMock,
        tg_channel: MagicMock,
        userbot_save_spy: AsyncMock,
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

        userbot_save_spy.assert_awaited_once()
        ctx.bot_registry.get_or_create.assert_called_once_with(BOT_ID, BOT_TOKEN)
        tg_bot.get_chat.assert_awaited_once_with(NEW_CHANNEL_ID)

    async def test_invalid_channel_input(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(ChannelNotFoundError):
            await ctx.update_channel.execute(ctx.owner, BOT_ID, "not-a-channel")

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.channel_id == CHANNEL_ID

    async def test_probe_rejects_non_channel(
        self, management_context: ManagementContext, tg_channel: MagicMock
    ):
        ctx = management_context
        tg_channel.type = "group"

        with pytest.raises(NotAChannelError):
            await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.channel_id == CHANNEL_ID

    async def test_probe_rejects_insufficient_permissions(
        self, management_context: ManagementContext, tg_bot: MagicMock, tg_channel: MagicMock
    ):
        ctx = management_context
        tg_channel.id = NEW_CHANNEL_ID
        tg_channel.full_name = NEW_CHANNEL_NAME
        tg_bot.get_chat_member = AsyncMock(
            return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=False)
        )

        with pytest.raises(InsufficientPermissionsError):
            await ctx.update_channel.execute(ctx.owner, BOT_ID, "987654321")

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.channel_id == CHANNEL_ID
        assert stored.channel_name == CHANNEL_NAME

    async def test_probe_rejects_non_admin_member(
        self, management_context: ManagementContext, tg_bot: MagicMock
    ):
        ctx = management_context
        tg_bot.get_chat_member = AsyncMock(return_value=MagicMock(status=ChatMemberStatus.MEMBER))

        with pytest.raises(InsufficientPermissionsError):
            await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.channel_id == CHANNEL_ID
        assert stored.channel_name == CHANNEL_NAME

    async def test_userbot_not_found(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.update_channel.execute(ctx.owner, BOT_ID + 1, str(CHANNEL_ID))

    async def test_banned_userbot(self, management_context: ManagementContext):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, banned=True)

        with pytest.raises(UserbotBanned):
            await ctx.update_channel.execute(ctx.owner, BOT_ID, str(CHANNEL_ID))

    async def test_rejects_foreign_user(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.update_channel.execute(ctx.stranger, BOT_ID, "987654321")

        stored = await ctx.userbot_service.get(BOT_ID)
        assert stored.channel_id == CHANNEL_ID
        assert stored.channel_name == CHANNEL_NAME


class TestDemoteAdmins:
    async def test_demotes_admins_except_owner(
        self, management_context: ManagementContext, user_dto_factory: Callable[..., UserDTO]
    ):
        ctx = management_context
        admins = [user_dto_factory() for _ in range(2)]
        regular = user_dto_factory()

        for user_dto in [*admins, regular]:
            ctx.created_user_ids.append(user_dto.user_id)
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

    async def test_demotes_without_admins_returns_zero(
        self, management_context: ManagementContext
    ):
        ctx = management_context

        assert await ctx.demote_admins.execute(ctx.owner, BOT_ID) == 0

    async def test_userbot_not_found(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.demote_admins.execute(ctx.owner, BOT_ID + 1)

    async def test_banned_userbot(self, management_context: ManagementContext):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, banned=True)

        with pytest.raises(UserbotBanned):
            await ctx.demote_admins.execute(ctx.owner, BOT_ID)

    async def test_rejects_foreign_user(
        self, management_context: ManagementContext, user_dto_factory: Callable[..., UserDTO]
    ):
        ctx = management_context
        admin = user_dto_factory()
        ctx.created_user_ids.append(admin.user_id)
        async with ctx.uow.transaction():
            await ctx.user_repo.create(admin)
            await ctx.profile_service.create(admin.user_id)
            await ctx.profile_service.update(admin.user_id, role=UserRole.ADMIN)

        with pytest.raises(UserbotNotFoundError):
            await ctx.demote_admins.execute(ctx.stranger, BOT_ID)

        profile = await ctx.profile_service.get(admin.user_id)
        assert profile.role == UserRole.ADMIN


class TestActiveToggle:
    async def test_active_userbot_becomes_inactive(
        self,
        management_context: ManagementContext,
        tg_bot: MagicMock,
        userbot_save_spy: AsyncMock,
    ):
        ctx = management_context

        result = await ctx.active_toggle.execute(ctx.owner, BOT_ID)

        assert result.active is False
        assert (await ctx.userbot_service.get(BOT_ID)).active is False
        userbot_save_spy.assert_awaited_once()
        ctx.remove_webhook.assert_awaited_once_with(tg_bot)
        ctx.set_webhook.assert_not_awaited()
        ctx.bot_registry.remove.assert_called_once_with(BOT_ID)

    async def test_inactive_userbot_becomes_active(
        self,
        management_context: ManagementContext,
        tg_bot: MagicMock,
        userbot_save_spy: AsyncMock,
    ):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, active=False)

        result = await ctx.active_toggle.execute(ctx.owner, BOT_ID)

        assert result.active is True
        assert (await ctx.userbot_service.get(BOT_ID)).active is True
        userbot_save_spy.assert_awaited_once()
        ctx.set_webhook.assert_awaited_once_with(tg_bot)
        ctx.remove_webhook.assert_not_awaited()
        ctx.bot_registry.remove.assert_not_called()

    async def test_probe_failure_deactivates_userbot(
        self, management_context: ManagementContext, tg_bot: MagicMock
    ):
        ctx = management_context
        tg_bot.get_chat = AsyncMock(
            side_effect=TelegramBadRequest(method="getChat", message="Chat not found")
        )

        with pytest.raises(BadRequestError):
            await ctx.active_toggle.execute(ctx.owner, BOT_ID)

        assert (await ctx.userbot_service.get(BOT_ID)).active is False
        ctx.remove_webhook.assert_awaited_once_with(tg_bot)
        ctx.set_webhook.assert_not_awaited()
        ctx.bot_registry.remove.assert_called_once_with(BOT_ID)

    async def test_invalid_token_deactivates_without_webhook_removal(
        self, management_context: ManagementContext, tg_bot: MagicMock
    ):
        ctx = management_context
        tg_bot.get_me = AsyncMock(
            side_effect=TelegramUnauthorizedError(method="getMe", message="Unauthorized")
        )

        with pytest.raises(InvalidTokenError):
            await ctx.active_toggle.execute(ctx.owner, BOT_ID)

        assert (await ctx.userbot_service.get(BOT_ID)).active is False
        ctx.remove_webhook.assert_not_awaited()
        ctx.bot_registry.remove.assert_called_once_with(BOT_ID)

    async def test_rejects_foreign_user(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.active_toggle.execute(ctx.stranger, BOT_ID)

        assert (await ctx.userbot_service.get(BOT_ID)).active is True
        ctx.set_webhook.assert_not_awaited()
        ctx.remove_webhook.assert_not_awaited()

    async def test_banned_userbot(self, management_context: ManagementContext):
        ctx = management_context
        async with ctx.uow.transaction():
            await ctx.userbot_service.update(BOT_ID, banned=True)

        with pytest.raises(UserbotBanned):
            await ctx.active_toggle.execute(ctx.owner, BOT_ID)

        assert (await ctx.userbot_service.get(BOT_ID)).active is True
        ctx.set_webhook.assert_not_awaited()
        ctx.remove_webhook.assert_not_awaited()

    async def test_userbot_not_found(self, management_context: ManagementContext):
        ctx = management_context

        with pytest.raises(UserbotNotFoundError):
            await ctx.active_toggle.execute(ctx.owner, BOT_ID + 1)
