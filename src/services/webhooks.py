
from logging import getLogger

from aiogram import Bot
from aiogram.methods import SetWebhook

from core.config import Config
from .cryptographer import Cryptographer

logger = getLogger("kita.webhook")

class WebhookService:

    def __init__(self, config: Config):
        self.config = config

        self.cryptographer = Cryptographer(config)

    async def set_webhook(self, bot: Bot, url: str | None = None) -> None:
        if not url:
            url = f"{self.config.webhook_base_url}/{bot.id}"

        current_webhook = await bot.get_webhook_info()
        if current_webhook.url == url and not self.config.webhook_force_update:
            logger.debug("Webhook already set for bot %s: %s", bot.id, url)
            return current_webhook

        if self.config.webhook_force_update:
            logger.info("Webhook force update enabled. Set/update webhook for bot %s", bot.id)

        secret_token = self.cryptographer.generate_bot_secret(bot.id)
        webhook_request = SetWebhook(
            url=url,
            secret_token=secret_token,
            drop_pending_updates=True,
        )

        if not await bot(webhook_request):
            logger.error("Failed to set webhook for bot %s", bot.id)
            raise RuntimeError(f"Could not set webhook for bot '{bot.id}'")

        logger.info("Webhook set successfully for bot %s", bot.id)
        return await bot.get_webhook_info()

    async def remove_webhook(self, bot: Bot):
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed for bot %s", bot.id)
