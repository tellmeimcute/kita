
from logging import getLogger

from aiogram import Bot
from dishka import Provider, Scope, provide
from config import Config, RuntimeConfig

from startup import get_runtime_config

logger = getLogger("kita.providers")

class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def config(self) -> Config:
        logger.info("Initializing Config instance")
        return Config()
    
    @provide(scope=Scope.APP)
    async def runtime_config(self, bot: Bot, config: Config) -> RuntimeConfig:
        logger.info("Initializing RuntimeConfig instance")
        return await get_runtime_config(bot, config)