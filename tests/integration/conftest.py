import os
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
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
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol


class TestProvider(Provider):
    scope = Scope.APP

    @provide
    def bot_registry_mock(self) -> BotRegistryProtocol:
        mock = AsyncMock(spec=BotRegistryProtocol)

        bot_mock = AsyncMock(spec=Bot)
        mock.get_current.return_value = bot_mock
        bot_mock.id = 6767

        return mock

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
