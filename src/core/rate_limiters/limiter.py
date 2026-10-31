import asyncio

from loguru import logger
from pydantic import BaseModel, Field
from redis.asyncio import Redis

# Returns {allowed, wait_ms, already_paused}:
#   {1, 0,        0} - allowed, one token spent
#   {0, wait_ms,  1} - already paused, do not warn again
#   {0, wait_ms,  0} - first denial: this call SET the pause and is the only
#                      one allowed to warn, so deny+silence is one atomic step
BUCKET_SCRIPT = """
local key           = KEYS[1]
local pause_key     = KEYS[2]
local rate          = tonumber(ARGV[1])
local max_tokens    = tonumber(ARGV[2])
local pause_buffer  = tonumber(ARGV[3])

local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

-- Pause check
local paused_until = tonumber(redis.call('GET', pause_key) or '0')
if paused_until > now then
  return {0, math.ceil((paused_until - now) * 1000), 1}
end

-- Token bucket
local data          = redis.call('HMGET', key, 'tokens', 'ts')
local tokens        = tonumber(data[1]) or max_tokens
local last_refill   = tonumber(data[2]) or now

tokens = math.min(max_tokens, tokens + (now - last_refill) * rate)

if tokens < 1 then
  redis.call('HSET', key, 'tokens', tostring(tokens), 'ts', tostring(now))
  redis.call('EXPIRE', key, math.ceil(max_tokens / rate) + 1)

  -- The pause is written here
  local wait_ms = math.ceil((1 - tokens) / rate * 1000) + pause_buffer
  redis.call('SET', pause_key, tostring(now + wait_ms / 1000),
             'EX', math.ceil(wait_ms / 1000) + 1)
  return {0, wait_ms, 0}
end

redis.call('HSET', key, 'tokens', tostring(tokens - 1), 'ts', tostring(now))
redis.call('EXPIRE', key, math.ceil(max_tokens / rate) + 1)
return {1, 0, 0}
"""

PAUSE_BUFFER_MS = 1000
MAX_SLEEP = 2.0


class LimiterResponse(BaseModel):
    allowed: bool
    paused: bool
    wait_ms: int = Field(ge=0)


class RateLimiter:
    def __init__(self, redis: Redis, *, rate: float, max_tokens: int):
        self._rate = rate
        self._max_tokens = max_tokens

        self._bucket_script = redis.register_script(BUCKET_SCRIPT)

    async def attempt(self, limit_key: str, pause_key: str) -> LimiterResponse:
        result = await self._bucket_script(
            keys=[limit_key, pause_key],
            args=[self._rate, self._max_tokens, PAUSE_BUFFER_MS],
        )

        result = LimiterResponse(allowed=result[0], wait_ms=result[1], paused=result[2])
        logger.debug("RateLimiter key {}: {}", limit_key, result)
        return result

    async def acquire(
        self,
        limit_key: str,
        pause_key: str,
        max_retries: int | None = None,
    ) -> None:
        retries = 0

        while True:
            res = await self.attempt(limit_key, pause_key)

            if res.allowed:
                return

            if max_retries and retries >= max_retries:
                logger.warning("RateLimiter key {}, timeout after {} retries", limit_key, retries)
                raise TimeoutError("Rate limit attempt timeout")

            retries += 1
            sleep_for = min(max(res.wait_ms, 1) / 1000, MAX_SLEEP)

            logger.debug("RateLimiter key {}, perform retry, sleep for {}", limit_key, sleep_for)
            await asyncio.sleep(sleep_for)
