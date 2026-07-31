import json
import logging
from typing import Generic, TypeVar, Set

from redis.asyncio import Redis
from pydantic import BaseModel, SecretStr

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("kita.redis")

class BaseRedisRepository(Generic[T]):
    model: type[T]
    expiry: int = 60

    exclude: Set[str] | None = None
    include: Set[str] | None = None

    @classmethod
    def _prepare_data(cls, data: T) -> dict:
        data_dict = data.model_dump(
            mode="python",
            exclude=cls.exclude,
            include=cls.include,
        )

        for k, v in data_dict.items():
            if isinstance(v, SecretStr):
                data_dict[k] = v.get_secret_value()

        return json.dumps(data_dict, default=str)

    @classmethod
    async def get(cls, redis: Redis, key: str) -> T | None:
        raw = await redis.get(key)
        if not raw:
            return None
        try:
            return cls.model.model_validate_json(raw)
        except Exception as e:
            logger.error("Fail to get key %s from cache: %s", key, e, exc_info=True)
            await cls.delete(redis, key)

    @classmethod
    async def set(cls, redis: Redis, key: str, data: T):
        to_cache_data = cls._prepare_data(data)

        await redis.set(
            name=key,
            value=to_cache_data,
            ex=cls.expiry,
        )

        logger.info("Cached key %s", key)

    @classmethod
    async def rpush(cls, redis: Redis, key: str, data: T):
        to_cache_data = cls._prepare_data(data)
        await redis.rpush(key, to_cache_data)
        await redis.expire(key, cls.expiry)

        logger.debug("RPUSH key %s", key)

    @classmethod
    async def lrange(
        cls, redis: Redis, key: str, start: int = 0, end: int = -1,
    ):
        raw_list = await redis.lrange(key, start, end)
        slice: list[T] = []

        for raw in raw_list:
            try:
                slice.append(cls.model.model_validate(json.loads(raw)))
            except Exception as e:
                logger.error("Error validate model from redis cache: %s", e, exc_info=True)
                continue

        return slice

    @classmethod
    async def delete(cls, redis: Redis, key: str):
        return await redis.delete(key)

    @classmethod
    async def exist(cls, redis: Redis, key: str):
        return bool(await redis.exists(key))