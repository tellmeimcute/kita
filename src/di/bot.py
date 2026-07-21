
from logging import getLogger

from redis.asyncio import Redis

from aiogram import Bot
from dishka import Provider, Scope, provide

from core.schemas import BotInfo
from core.consts import T_ME
from database.redis import BotInfoRedis, RedisKey, KitaKeyBuilder
from interfaces import BotRegistryProtocol
from services import BotRegistry

logger = getLogger("kita.providers")

class BotProvider(Provider):
    bot_registry = provide(source=BotRegistry, provides=BotRegistryProtocol, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    def get_bot(self, registry: BotRegistryProtocol) -> Bot:
        bot = registry.get_current()
        if bot is not None:
            return bot
        raise ValueError("No Bot available in current context")


    @provide(scope=Scope.REQUEST)
    async def bot_info(self, redis: Redis, bot: Bot) -> BotInfo:
        logger.debug("Initializing BotInfo instance")

        key_builder = KitaKeyBuilder(with_user_id=False)
        key = key_builder.build(RedisKey(bot_id=bot.id), "bot_config")

        bot_info = await BotInfoRedis.get(redis, key)
        if bot_info:
            return bot_info

        channel_info = "HERE SHOULD BE CHANNEL NAME"
        bot_user = await bot.get_me()

        bot_info = BotInfo(
            bot_id=bot.id,
            channel_name=channel_info,
            bot_username=bot_user.username,
            bot_url=f"{T_ME}{bot_user.username}",
        )

        await BotInfoRedis.set(redis, key, bot_info)
        return bot_info
    