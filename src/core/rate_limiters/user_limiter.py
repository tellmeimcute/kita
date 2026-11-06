from redis.asyncio import Redis

from database.dto import UserDTO
from database.redis import KitaKeyBuilder, RedisKey
from interfaces import BotContextProtocol

from .limiter import LimiterResponse, RateLimiter


class UserLimiter:
    """Token-bucket limiter bound to a (bot_id, user_id) pair.

    The ``scope`` isolates independent limiters from one another:
    each has its own bucket and its own cooldown/pause.
    """

    def __init__(
        self,
        redis: Redis,
        bot_context: BotContextProtocol,
        *,
        scope: str,
        max_tokens: int = 5,
        refill_rate: float = 0.3,
    ):
        self._bot_context = bot_context
        self._limiter = RateLimiter(redis, rate=refill_rate, max_tokens=max_tokens)
        self._key_builder = KitaKeyBuilder()
        self._scope = scope

    @property
    def bot(self):
        return self._bot_context.get_current()

    def _keys(self, user_dto: UserDTO) -> tuple[str, str]:
        keybase = RedisKey(bot_id=self.bot.id, user_id=user_dto.user_id)
        return (
            self._key_builder.build(keybase, ["rate_limit", self._scope]),
            self._key_builder.build(keybase, ["rate_limit", self._scope, "pause"]),
        )

    async def attempt(self, user_dto: UserDTO) -> LimiterResponse:
        limit_key, pause_key = self._keys(user_dto)
        return await self._limiter.attempt(limit_key, pause_key)
