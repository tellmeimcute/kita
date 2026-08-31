from database.redis import KitaKeyBuilder, RedisKey
from database.redis.base import BaseRedisRepository
from interfaces import BotRegistryProtocol


class CachedRepository:
    REDIS_KEY_PART = "base_key"

    __slots__ = (
        "_bot_registry",
        "_key_builder",
        "_redis",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        redis: BaseRedisRepository,
        key_builder: KitaKeyBuilder | None = None,
    ):
        self._bot_registry = bot_registry
        self._redis = redis

        if key_builder:
            self._key_builder = key_builder
        else:
            self._key_builder = KitaKeyBuilder()

    def _get_key(self, user_id: int):
        redis_key = RedisKey(bot_id=self.bot.id, user_id=user_id)
        return self._key_builder.build(redis_key, self.REDIS_KEY_PART)

    async def _cache_or_load(
        self,
        key: str,
        loader,
        *,
        redis_repo: BaseRedisRepository | None = None,
    ):
        redis = redis_repo or self._redis

        if (hit := await redis.get(key)) is not None:
            return hit

        result = await loader()

        if result is not None:
            await redis.set_cache(key, result)
        return result

    @property
    def bot(self):
        return self._bot_registry.get_current()
