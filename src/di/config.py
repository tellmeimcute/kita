
from logging import getLogger

from aiogram import Bot
from dishka import Provider, Scope, provide
from core.config import Config, RuntimeConfig

from core.consts import T_ME

logger = getLogger("kita.providers")

class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def config(self) -> Config:
        logger.info("Initializing Config instance")
        return Config()
    
    @provide(scope=Scope.APP)
    async def runtime_config(self, bot: Bot, config: Config) -> RuntimeConfig:
        logger.info("Initializing RuntimeConfig instance")

        channel_info = await bot.get_chat(config.CHANNEL_ID)
        bot_user = await bot.get_me()

        runtime_config = RuntimeConfig(
            channel_name=channel_info.full_name,
            bot_username=bot_user.username,
            bot_url=f"{T_ME}{bot_user.username}",
        )

        return runtime_config