import os
from collections.abc import Callable, Generator
from itertools import count
from unittest.mock import MagicMock

import pytest
from aiogram.types import Message
from alembic import command
from alembic.config import Config as AlembicConfig
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import AsyncRedisContainer

from core.config import Config
from di import (
    BotProvider,
    ConfigProvider,
    DatabaseProvider,
    RedisProvider,
    RepositoryProvider,
    ServiceProvider,
    UseCaseProvider,
    UtilsProvider,
)
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, WebhookServiceProtocol

from .factories import make_tg_message as build_tg_message
from .scaffold import FakeBotRegistry, FakeWebhookService


class TestProvider(Provider):
    scope = Scope.APP

    @provide
    def bot_registry_mock(self) -> BotRegistryProtocol:
        return FakeBotRegistry()

    @provide
    def webhook_service_mock(self) -> WebhookServiceProtocol:
        return FakeWebhookService()

    @provide
    def postgres_docker(self) -> Generator[PostgresContainer]:
        container = PostgresContainer(
            "postgres:17-alpine",
            username="postgres",
            password="test_password",
            dbname="kita_test",
            driver="asyncpg",
        )

        container.start()

        os.environ["POSTGRES_HOST"] = container.get_container_host_ip()
        os.environ["POSTGRES_PORT"] = str(container.get_exposed_port(5432))
        os.environ["POSTGRES_USER"] = container.username
        os.environ["POSTGRES_PASSWORD"] = container.password
        os.environ["POSTGRES_DB"] = container.dbname

        alembic_cfg = AlembicConfig("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", container.get_connection_url())
        command.upgrade(alembic_cfg, "head")

        yield container

        container.stop()

    @provide
    def redis_docker(self) -> Generator[AsyncRedisContainer]:
        container = AsyncRedisContainer(
            "redis:7-alpine",
        )
        container.start()

        os.environ["REDIS_HOST"] = container.get_container_host_ip()
        os.environ["REDIS_PORT"] = str(container.get_exposed_port(6379))

        yield container

        container.stop()

    @provide
    def config(
        self,
        postgres_docker: PostgresContainer,
        redis_docker: AsyncRedisContainer,
    ) -> Config:
        return Config()


@pytest.fixture(scope="session", autouse=True)
async def dishka_container():
    container = make_async_container(
        ConfigProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        UseCaseProvider(),
        BotProvider(),
        UtilsProvider(),
        DatabaseProvider(),
        RedisProvider(),
        TestProvider(),
    )

    yield container

    await container.close()


@pytest.fixture()
async def request_container(dishka_container: AsyncContainer):
    async with dishka_container() as req:
        yield req


@pytest.fixture
async def bot_registry(request_container: AsyncContainer) -> FakeBotRegistry:
    registry: FakeBotRegistry = await request_container.get(BotRegistryProtocol)
    registry.reset()
    return registry


@pytest.fixture
async def webhook_service(request_container: AsyncContainer) -> FakeWebhookService:
    service: FakeWebhookService = await request_container.get(WebhookServiceProtocol)
    service.reset()
    return service


@pytest.fixture
async def tg_bot(bot_registry: FakeBotRegistry) -> MagicMock:
    return bot_registry.bot


@pytest.fixture
async def tg_channel(bot_registry: FakeBotRegistry) -> MagicMock:
    return bot_registry.channel


@pytest.fixture(autouse=True)
async def clean_state(request_container: AsyncContainer):
    redis = await request_container.get(Redis)
    session = await request_container.get(AsyncSession)
    uow = await request_container.get(UnitOfWorkProtocol)

    await redis.flushdb()

    async with uow.transaction():
        result = await session.execute(
            text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'alembic_version'
        """)
        )

        tables = [row[0] for row in result.fetchall()]

        assert tables

        tables_str = ", ".join(f'"{table}"' for table in tables)
        await session.execute(text("SET LOCAL lock_timeout = '5s'"))
        await session.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE"))

    yield


@pytest.fixture
def make_tg_message() -> Callable[..., Message]:
    message_ids = count(start=1)

    def _make_message(**kwargs) -> Message:
        return build_tg_message(message_id=next(message_ids), **kwargs)

    return _make_message


@pytest.fixture
def make_tg_album(make_tg_message: Callable[..., Message]) -> Callable[..., list[Message]]:
    def _make_album(media_count: int = 2, *, caption: str | None = None) -> list[Message]:
        return [
            make_tg_message(
                photo=f"photo-{index}",
                caption=caption if index == 0 else None,
                media_group_id="album",
            )
            for index in range(media_count)
        ]

    return _make_album
