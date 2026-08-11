from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from loguru import logger
from redis.asyncio import ConnectionPool, Redis

from core.config import Config
from database.redis import (
    TgMessageRedis,
    UserBotRedis,
    UserProfileRedis,
    UserRedis,
    UserStatsRedis,
)


class RedisProvider(Provider):
    scope = Scope.APP

    user_stats_redis = provide(UserStatsRedis)
    user_redis = provide(UserRedis)
    user_profile_redis = provide(UserProfileRedis)
    user_bot_redis = provide(UserBotRedis)
    tg_message_redis = provide(TgMessageRedis)

    @provide
    async def redis(self, config: Config) -> AsyncIterable[Redis]:
        logger.info("Initializing Redis instance")
        connection_pool = ConnectionPool.from_url(config.redis.redis_url, decode_responses=True)
        redis = Redis(connection_pool=connection_pool)

        try:
            await redis.ping()
            logger.info("Redis connected")
        except Exception:
            logger.error("Redis connection failed")
            raise

        yield redis

        logger.info("Closing Redis connection")
        await redis.aclose()
