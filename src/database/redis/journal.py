from dataclasses import dataclass
from typing import Any

from loguru import logger

from database.redis.base import BaseRedisRepository

_DELETE = object()


@dataclass(frozen=True, slots=True)
class CacheOp:
    redis: BaseRedisRepository
    key: str
    payload: Any


class CacheJournal:
    """
    Cache operations apply only after a successful COMMIT.
    """

    __slots__ = ("_pending", "_depth")

    def __init__(self) -> None:
        self._pending: dict[tuple[int, str], CacheOp] = {}
        self._depth = 0

    @property
    def active(self) -> bool:
        return self._depth > 0

    def begin(self) -> None:
        self._depth += 1

    def end(self) -> None:
        self._depth = max(self._depth - 1, 0)

    async def set(self, redis: BaseRedisRepository, key: str, data: Any) -> None:
        if not self.active:
            await redis.set_cache(key, data)
            return
        self._pending[(id(redis), key)] = CacheOp(redis, key, redis.serialize(data))

    async def invalidate(self, redis: BaseRedisRepository, key: str) -> None:
        if not self.active:
            await redis.delete(key)
            return
        self._pending[(id(redis), key)] = CacheOp(redis, key, _DELETE)

    async def flush(self) -> None:
        pending, self._pending = self._pending, {}

        for op in pending.values():
            try:
                if op.payload is _DELETE:
                    await op.redis.delete(op.key)
                else:
                    await op.redis.set_payload(op.key, op.payload)
            except Exception:
                logger.exception("Failed to apply cache op for key {}", op.key)

    def discard(self) -> None:
        self._pending.clear()
