
from typing import Literal
from logging import getLogger
from dataclasses import dataclass
from datetime import datetime, timezone
from redis.asyncio import Redis
from database.dto import UserDTO


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

logger = getLogger("kita.rate_limit")

@dataclass
class TokenBucketResult:
    allowed: int
    remains: int

class TokenBucketLimiter:

    def __init__(
        self,
        redis: Redis,
        max_tokens: int = 5,
        refill_rate: float = 0.3,
    ):
        self._redis = redis
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate

        self.WARNED_TTL =  int((1 / refill_rate) + 1)
        self._script = SCRIPT
    
    def get_user_key(
        self,
        user_dto: UserDTO,
        action: Literal["ALL", "CALLBACK", "MESSAGE", "WARNED"]
    ):
        return f"rate_limit:{user_dto.user_id}:{action}"

    async def mark_warned(self, user_dto: UserDTO):
        key = self.get_user_key(user_dto, "WARNED")
        await self._redis.sadd(key, "1")
        await self._redis.expire(key, self.WARNED_TTL)

    async def unmark_warned(self, user_dto: UserDTO):
        key = self.get_user_key(user_dto, "WARNED")
        await self._redis.srem(key, "1")

    async def is_warned(self, user_dto: UserDTO) -> bool:
        key = self.get_user_key(user_dto, "WARNED")
        return await self._redis.sismember(key, "1")

    async def attempt(
        self,
        user_dto: UserDTO,
        action: Literal["ALL", "CALLBACK", "MESSAGE"] = "ALL"
    ) -> TokenBucketResult:
        key = self.get_user_key(user_dto, action)
        now = datetime.now(timezone.utc)

        result = await self._redis.eval(
            self._script, 1, key, self._max_tokens, self._refill_rate, now.timestamp()
        )

        result = TokenBucketResult(*result)
        logger.debug("UserID %s : %s", user_dto.user_id, result)

        return result
