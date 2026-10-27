from collections.abc import Callable
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.cryptographer import Cryptographer
from database.dto import UserDTO
from database.repository import UserRepository
from interfaces import (
    UnitOfWorkProtocol,
    UserBotRepositoryProtocol,
    UserBotServiceProtocol,
    UserProfileServiceProtocol,
)
from usecases import (
    UserbotActiveToggleUseCase,
    UserbotDemoteAdminsUseCase,
    UserBotRegisterUseCase,
    UserbotUpdateChannelUseCase,
    UserbotUpdateTokenUseCase,
)

from ..scaffold import (
    BOT_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    CHANNEL_ID,
    CHANNEL_NAME,
    FakeBotRegistry,
    FakeWebhookService,
)


@dataclass(frozen=True)
class BaseContext:
    uow: UnitOfWorkProtocol
    userbot_service: UserBotServiceProtocol
    bot_registry: FakeBotRegistry
    session_maker: async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class UserBotTestContext(BaseContext):
    register: UserBotRegisterUseCase
    userbot_repo: UserBotRepositoryProtocol
    owner_id: int
    raw_token: str


@dataclass(frozen=True)
class ManagementContext(BaseContext):
    update_token: UserbotUpdateTokenUseCase
    update_channel: UserbotUpdateChannelUseCase
    demote_admins: UserbotDemoteAdminsUseCase
    active_toggle: UserbotActiveToggleUseCase
    user_repo: UserRepository
    profile_service: UserProfileServiceProtocol
    set_webhook: AsyncMock
    remove_webhook: AsyncMock
    owner: UserDTO
    stranger: UserDTO


@pytest.fixture
async def userbot_test_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
    bot_registry: FakeBotRegistry,
) -> UserBotTestContext:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo = await request_container.get(UserRepository)
    crypto = await request_container.get(Cryptographer)

    owner_dto = user_dto_factory()
    async with uow.transaction():
        await user_repo.create(owner_dto)

    return UserBotTestContext(
        uow=uow,
        register=await request_container.get(UserBotRegisterUseCase),
        userbot_service=await request_container.get(UserBotServiceProtocol),
        userbot_repo=await request_container.get(UserBotRepositoryProtocol),
        bot_registry=bot_registry,
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
        owner_id=owner_dto.user_id,
        raw_token=crypto.encrypt(BOT_TOKEN),
    )


@pytest.fixture
async def management_context(
    request_container: AsyncContainer,
    user_dto_factory: Callable[..., UserDTO],
    bot_registry: FakeBotRegistry,
    webhook_service: FakeWebhookService,
) -> ManagementContext:
    uow = await request_container.get(UnitOfWorkProtocol)
    user_repo = await request_container.get(UserRepository)
    userbot_service = await request_container.get(UserBotServiceProtocol)
    profile_service = await request_container.get(UserProfileServiceProtocol)

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

    return ManagementContext(
        uow=uow,
        update_token=await request_container.get(UserbotUpdateTokenUseCase),
        update_channel=await request_container.get(UserbotUpdateChannelUseCase),
        demote_admins=await request_container.get(UserbotDemoteAdminsUseCase),
        active_toggle=await request_container.get(UserbotActiveToggleUseCase),
        userbot_service=userbot_service,
        user_repo=user_repo,
        profile_service=profile_service,
        set_webhook=webhook_service.set_webhook,
        remove_webhook=webhook_service.remove_webhook,
        bot_registry=bot_registry,
        session_maker=await request_container.get(async_sessionmaker[AsyncSession]),
        owner=owner,
        stranger=stranger,
    )
