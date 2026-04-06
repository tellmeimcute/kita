
import logging
from typing import Generic, TypeVar
from redis.asyncio import Redis
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("kita.redis")

class BaseRedisRepository(Generic[T]):
    model: type[T]
    expiry: int = 60

    @classmethod
    async def get(cls, redis: Redis, key: str) -> T:
        raw = await redis.get(key)
        if not raw:
            return None
        try:
            return cls.model.model_validate_json(raw)
        except Exception as e:
            logger.error("Fail to get user from cache: %s", e, exc_info=True)
            await cls.delete(redis, key)

    @classmethod
    async def set(cls, redis: Redis, key: str, data: T):
        data = data.model_dump_json()
        await redis.set(
            name=key,
            value=data,
            ex=cls.expiry,
        )

        logger.info("Cached key %s", key)

    @classmethod
    async def delete(cls, redis: Redis, key: str):
        return await redis.delete(key)

    @classmethod
    async def exist(cls, redis: Redis, key: str):
        return bool(await redis.exists(key))