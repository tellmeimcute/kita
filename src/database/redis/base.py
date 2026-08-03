import json
import logging
from collections.abc import Sequence
from types import UnionType
from typing import Union, get_args, get_origin

from pydantic import BaseModel, SecretStr

from core.cryptographer import Cryptographer
from redis.asyncio import Redis

logger = logging.getLogger("kita.redis")


class BaseRedisRepository[T: BaseModel]:
    model: type[T]
    expiry: int = 3600

    exclude: set[str] | None = None
    include: set[str] | None = None

    _secret_fields: set[str] = set()

    __slots__ = (
        "_redis",
        "_crypto",
    )

    def __init__(self, redis: Redis, crypto: Cryptographer):
        self._redis = redis
        self._crypto = crypto

    def _is_secret_field(self, field_name: str) -> bool:
        if field_name in self._secret_fields:
            return True

        field_info = self.model.model_fields.get(field_name)
        if not field_info:
            return False

        annotation = field_info.annotation

        if get_origin(annotation) in {Union, UnionType}:
            return SecretStr in get_args(annotation)

        return annotation is SecretStr

    def _prepare_cache(self, data: T) -> str:
        data_dict = data.model_dump(
            mode="python",
            exclude=self.exclude,
            include=self.include,
        )

        for k, v in data_dict.items():
            if v is not None and self._is_secret_field(k):
                if isinstance(v, SecretStr):
                    data_dict[k] = self._crypto.encrypt(str(v.get_secret_value()))
                else:
                    data_dict[k] = self._crypto.encrypt(str(v))

        return json.dumps(data_dict, default=str)

    def _from_cache(self, cached_str: str) -> T:
        data_dict: dict = json.loads(cached_str)

        for k, v in data_dict.items():
            if v is not None and self._is_secret_field(k):
                data_dict[k] = self._crypto.decrypt(str(v))

        return self.model.model_validate(data_dict)

    async def get(self, key: str) -> T | None:
        raw = await self._redis.get(key)
        if not raw:
            return None
        try:
            return self._from_cache(raw)
        except Exception as e:
            logger.error("Fail to get key %s from cache: %s", key, e, exc_info=True)
            await self.delete(key)
            return None

    async def set_cache(self, key: str, data: T):
        await self._redis.set(
            name=key,
            value=self._prepare_cache(data),
            ex=self.expiry,
        )

        logger.info("Cached key %s", key)

    async def rpush(self, key: str, *datas: T):
        to_cache_data = (self._prepare_cache(data) for data in datas)
        await self._redis.rpush(key, *to_cache_data)
        await self._redis.expire(key, self.expiry)

        logger.debug("RPUSH key %s", key)

    async def lrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
    ) -> Sequence[T]:
        raw_list = await self._redis.lrange(key, start, end)
        items: list[T] = []

        for raw in raw_list:
            try:
                items.append(self._from_cache(raw))
            except Exception as e:
                logger.error("Error validate model from redis cache: %s", e, exc_info=True)
                continue

        return items

    async def delete(self, key: str):
        return await self._redis.delete(key)

    async def exist(self, key: str):
        return bool(await self._redis.exists(key))
