from types import UnionType
from typing import Any, Union, get_args, get_origin

from loguru import logger
from pydantic import BaseModel, SecretStr, TypeAdapter

from core.cryptographer import Cryptographer
from redis.asyncio import Redis


class BaseRedisRepository[T]:
    model: type[BaseModel] | None = None
    adapter: TypeAdapter | None = None

    expiry: int = 3600

    exclude: set[str] | None = None
    include: set[str] | None = None

    _secret_fields: set[str] = set()

    __slots__ = (
        "_redis",
        "_crypto",
        "_any_adapter",
    )

    def __init__(self, redis: Redis, crypto: Cryptographer):
        self._redis = redis
        self._crypto = crypto
        self._any_adapter = TypeAdapter(Any)

        if not self.model and not self.adapter:
            raise ValueError("Either model or adapter should be provided!")

    def _is_secret_field(self, field_name: str) -> bool:
        if field_name in self._secret_fields:
            return True

        if not self.model:
            return False

        field_info = self.model.model_fields.get(field_name)
        if not field_info:
            return False

        annotation = field_info.annotation

        if get_origin(annotation) in {Union, UnionType}:
            return SecretStr in get_args(annotation)

        return annotation is SecretStr

    def _encrypt_fields(self, data_dict: dict):
        for k, v in data_dict.items():
            if v is not None and self._is_secret_field(k):
                if isinstance(v, SecretStr):
                    data_dict[k] = self._crypto.encrypt(str(v.get_secret_value()))
                else:
                    data_dict[k] = self._crypto.encrypt(str(v))

    def _decrypt_fields(self, data_dict: dict):
        for k, v in data_dict.items():
            if v is not None and self._is_secret_field(k):
                data_dict[k] = self._crypto.decrypt(str(v))

    def _prepare_cache(self, data: T) -> bytes:
        if self.model and not isinstance(data, BaseModel):
            raise TypeError("RedisRepo with provided model should take a BaseModel subclass only")

        if self.model and isinstance(data, BaseModel):
            data_dict = data.model_dump(
                mode="python",
                exclude=self.exclude,
                include=self.include,
            )
        elif self.adapter:
            data_dict = self.adapter.dump_python(data)

        if isinstance(data_dict, dict):
            self._encrypt_fields(data_dict)

        return self._any_adapter.dump_json(data_dict)

    def _from_cache(self, cached_value: str) -> T:
        raw_data = self._any_adapter.validate_json(cached_value)

        if isinstance(raw_data, dict):
            self._decrypt_fields(raw_data)

        if self.model:
            return self.model.model_validate(raw_data)
        if self.adapter:
            return self.adapter.validate_python(raw_data)

    async def get(self, key: str) -> T | None:
        raw = await self._redis.get(key)
        if not raw:
            return None
        try:
            return self._from_cache(raw)
        except Exception as e:
            logger.exception("Fail to get key {} from cache: {}", key, e)
            await self.delete(key)
            return None

    async def set_cache(self, key: str, data: T):
        await self._redis.set(
            name=key,
            value=self._prepare_cache(data),
            ex=self.expiry,
        )

        logger.info("Cached key {}", key)

    async def rpush(self, key: str, *datas: T):
        to_cache_data = (self._prepare_cache(data) for data in datas)
        await self._redis.rpush(key, *to_cache_data)
        await self._redis.expire(key, self.expiry)

        logger.debug("RPUSH key {}", key)

    async def lrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
    ) -> list[T]:
        raw_list = await self._redis.lrange(key, start, end)
        try:
            return [self._from_cache(v) for v in raw_list]
        except Exception as e:
            await self.delete(key)
            logger.exception("Error validate model from redis cache: {}", e)
        return []

    async def delete(self, key: str):
        return await self._redis.delete(key)

    async def exist(self, key: str):
        return bool(await self._redis.exists(key))
