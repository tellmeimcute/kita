
from logging import getLogger
from collections.abc import AsyncIterable
from dishka import Provider, Scope, provide

from redis.asyncio import Redis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from core.config import Config

logger = getLogger("kita.providers")

class BotProvider(Provider):

    @provide(scope=Scope.APP)
    async def bot(self, config: Config) -> AsyncIterable[Bot]:
        logger.info("Initializing Bot instance")

        async with Bot(
            token=config.TG_TOKEN.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=AiohttpSession(proxy=config.PROXY),
        ) as bot:
            yield bot
        
        logger.info("Closing Bot session")
        await bot.session.close()

    @provide(scope=Scope.APP)
    def dp(self, redis: Redis) -> Dispatcher:
        logger.info("Initializing Dispatcher instance")
        storate = RedisStorage(redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))
        dp = Dispatcher(storage=storate, name="dispatcher")
        return dp
    