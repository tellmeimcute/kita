from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from loguru import logger
from redis.asyncio import Redis

from database.dto import UserDTO
from database.redis import KitaKeyBuilder, RedisKey
from interfaces import BotRegistryProtocol

# https://redis.io/tutorials/howtos/ratelimiting/#4-token-bucket

SCRIPT = """
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local data = redis.call('HGETALL', key)
local tokens = max_tokens
local last_refill = now

if #data > 0 then
  local fields = {}
  for i = 1, #data, 2 do
    fields[data[i]] = data[i + 1]
  end
  tokens = tonumber(fields['tokens']) or max_tokens
  last_refill = tonumber(fields['last_refill']) or now
end

-- Refill tokens based on elapsed time
local elapsed = now - last_refill
local new_tokens = elapsed * refill_rate
tokens = math.min(max_tokens, tokens + new_tokens)

local allowed = 0
local remaining = tokens

if tokens >= 1 then
  tokens = tokens - 1
  remaining = tokens
  allowed = 1
end

redis.call('HSET', key, 'tokens', tostring(tokens), 'last_refill', tostring(now))
redis.call('EXPIRE', key, math.ceil(max_tokens / refill_rate) + 1)

return { allowed, math.floor(remaining) }
"""


@dataclass
class TokenBucketResult:
    allowed: int
    remains: int


class TokenBucketLimiter:
    def __init__(
        self,
        redis: Redis,
        bot_registry: BotRegistryProtocol,
        max_tokens: int = 5,
        refill_rate: float = 0.3,
    ):
        self._redis = redis
        self._bot_registry = bot_registry
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate
        self._key_builder = KitaKeyBuilder()

        self.WARNED_TTL = int((1 / refill_rate) + 1)
        self._script = SCRIPT

    def get_user_key(self, user_dto: UserDTO, action: str):
        bot = self._bot_registry.get_current()
        return self._key_builder.build(
            RedisKey(bot_id=bot.id, user_id=user_dto.user_id), f"rate_limit_{action.lower()}"
        )

    async def mark_warned(
        self, user_dto: UserDTO, warn_key: Literal["WARNED", "USERBOT_WARNED"] = "WARNED"
    ):
        key = self.get_user_key(user_dto, warn_key)
        await self._redis.sadd(key, "1")
        await self._redis.expire(key, self.WARNED_TTL)

    async def unmark_warned(
        self, user_dto: UserDTO, warn_key: Literal["WARNED", "USERBOT_WARNED"] = "WARNED"
    ):
        key = self.get_user_key(user_dto, warn_key)
        await self._redis.srem(key, "1")

    async def is_warned(
        self, user_dto: UserDTO, warn_key: Literal["WARNED", "USERBOT_WARNED"] = "WARNED"
    ) -> bool:
        key = self.get_user_key(user_dto, warn_key)
        return await self._redis.sismember(key, "1")

    async def attempt(
        self,
        user_dto: UserDTO,
        action: Literal["ALL", "TG_UPDATE", "USERBOT_ACTION"] = "TG_UPDATE",
    ) -> TokenBucketResult:
        key = self.get_user_key(user_dto, action)
        now = datetime.now(UTC)

        result = await self._redis.eval(
            self._script, 1, key, self._max_tokens, self._refill_rate, now.timestamp()
        )

        result = TokenBucketResult(*result)
        logger.debug("RedisKey {} : {}", key, result)

        return result
