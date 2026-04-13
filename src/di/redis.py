

from logging import getLogger
from collections.abc import AsyncIterable

from core.config import Config
from dishka import Provider, Scope, provide
from redis.asyncio import ConnectionPool, Redis

logger = getLogger("kita.providers")


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