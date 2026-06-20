

from logging import getLogger
from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from redis.asyncio import ConnectionPool, Redis

from core.config import Config
from core.rate_limiters import TokenBucketLimiter

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

    @provide(scope=Scope.APP)
    def token_bucket(self, config: Config, redis: Redis) -> TokenBucketLimiter:
        logger.info("Initializing TokenBucketLimiter instance")
        kwargs = config.rate_limit.model_dump()
        return TokenBucketLimiter(redis, **kwargs)