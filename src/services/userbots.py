
from redis.asyncio import Redis
from database.dto import UserBotDTO
from database.redis import UserBotRedis, KitaKeyBuilder, RedisKey
from interfaces import UserBotRepositoryProtocol, BotRegistryProtocol

class UserBotService:

    __slots__ = (
        "redis",
        "repo",
        "key_builder",
        "bot_registry"
    )

    def __init__(
        self,
        redis: Redis,
        repo: UserBotRepositoryProtocol,
        bot_registry: BotRegistryProtocol,
    ):
        self.redis = redis
        self.repo = repo
        self.bot_registry = bot_registry
        self.key_builder = KitaKeyBuilder(with_user_id=False)

    def _get_key(self, bot_id: int):
        redis_key = RedisKey(bot_id=bot_id)
        return self.key_builder.build(key=redis_key, part="bot")

    async def get(self, bot_id: int) -> UserBotDTO | None:
        cached_bot = await UserBotRedis.get(self.redis, self._get_key(bot_id))
        if cached_bot:
            return cached_bot

        userbot_dto = await self.repo.get(bot_id)
        if not userbot_dto:
            return None

        await UserBotRedis.set(
            redis=self.redis,
            key=self._get_key(bot_id),
            data=userbot_dto,
        )

        return userbot_dto

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ):
        return await self.repo.create(
            token, bot_id, username, owner_id, channel_id, channel_name
        )
    