import json
import logging
from typing import Sequence, Generic, Set, TypeVar, get_origin, get_args, Union
from types import UnionType

from pydantic import BaseModel, SecretStr
from redis.asyncio import Redis

from core.config import Config
from services.cryptographer import Cryptographer

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("kita.redis")

class BaseRedisRepository(Generic[T]):
    crypto = Cryptographer(Config.get())
    _secret_fields: set[str] = set()

    model: type[T]
    expiry: int = 3600

    exclude: Set[str] | None = None
    include: Set[str] | None = None

    @classmethod
    def _is_secret_field(cls, field_name: str):
        if field_name in cls._secret_fields:
            return True

        field_info = cls.model.model_fields.get(field_name)
        if not field_info:
            return False
        
        annotation = field_info.annotation

        if get_origin(annotation) in (Union, UnionType):
            return SecretStr in get_args(annotation)
        
        return annotation is SecretStr

    @classmethod
    def _prepare_cache(cls, data: T) -> dict:
        data_dict = data.model_dump(
            mode="json",
            exclude=cls.exclude,
            include=cls.include,
        )

        for k, v in data_dict.items():
            if v is not None and cls._is_secret_field(k):
                data_dict[k] = cls.crypto.encrypt(str(v))

        return json.dumps(data_dict, default=str)

    @classmethod
    def _from_cache(cls, cached_str: str):
        data_dict: dict = json.loads(cached_str)
        
        for k, v in data_dict.items():
            if v is not None and cls._is_secret_field(k):
                data_dict[k] = cls.crypto.decrypt(str(v))

        return cls.model.model_validate(data_dict)

    @classmethod
    async def get(cls, redis: Redis, key: str) -> T | None:
        raw = await redis.get(key)
        if not raw:
            return None
        try:
            return cls._from_cache(raw)
        except Exception as e:
            logger.error("Fail to get key %s from cache: %s", key, e, exc_info=True)
            await cls.delete(redis, key)

    @classmethod
    async def set_cache(cls, redis: Redis, key: str, data: T):
        to_cache_data = cls._prepare_cache(data)

        await redis.set(
            name=key,
            value=to_cache_data,
            ex=cls.expiry,
        )

        logger.info("Cached key %s", key)

    @classmethod
    async def rpush(cls, redis: Redis, key: str, *datas: T):
        to_cache_data = (cls._prepare_cache(data) for data in datas)
        await redis.rpush(key, *to_cache_data)
        await redis.expire(key, cls.expiry)

        logger.debug("RPUSH key %s", key)

    @classmethod
    async def lrange(
        cls, redis: Redis, key: str, start: int = 0, end: int = -1,
    ) -> Sequence[T]:
        raw_list = await redis.lrange(key, start, end)
        slice: list[T] = []

        for raw in raw_list:
            try:
                slice.append(cls._from_cache(raw))
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