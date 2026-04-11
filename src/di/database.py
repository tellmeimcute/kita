
import asyncio
from logging import getLogger
from collections.abc import AsyncIterable
from dishka import Provider, Scope, provide

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from redis.asyncio import Redis, ConnectionPool

from database import DatabaseManager
from core.config import Config

logger = getLogger("kita.providers")


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def db_manager(self, config: Config) -> AsyncIterable[DatabaseManager]:
        logger.info("Initializing DatabaseManager instance")
        manager = DatabaseManager(config)
        yield manager

        logger.info("Dispose DB engine")
        await asyncio.sleep(0.2)
        await manager.engine.dispose()

    @provide(scope=Scope.APP)
    def session_maker(self, db_manager: DatabaseManager) -> async_sessionmaker[AsyncSession]:
        return db_manager.session_maker

    @provide(scope=Scope.REQUEST)
    async def session(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        logger.debug("Initializing AsyncSession instance")
        async with session_maker() as session:
            yield session


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def redis(self, config: Config) -> AsyncIterable[Redis]:
        logger.info("Initializing Redis instance")
        connection_pool = ConnectionPool.from_url(config.redis.redis_url, decode_responses=True)
        redis = Redis(connection_pool=connection_pool)

        try:
            await redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error("Redis connection failed")
            raise

        yield redis

        logger.info("Closing Redis connection")
        await redis.aclose()
