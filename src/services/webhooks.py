from collections.abc import Sequence

from aiogram import Bot
from aiogram.methods import SetWebhook
from aiogram.types import WebhookInfo
from loguru import logger

from core.config import Config
from core.cryptographer import Cryptographer


class WebhookService:
    def __init__(self, config: Config, crypto: Cryptographer):
        self.config = config
        self.cryptographer = crypto

    async def set_webhook(
        self,
        bot: Bot,
        *,
        allowed_updates: Sequence[str],
        url: str | None = None,
        force_update: bool = False,
    ) -> WebhookInfo:
        webhook_url = url or f"{self.config.webhook_base_url}/{bot.id}"
        should_force = force_update or self.config.webhook.force_update
        current_webhook = await bot.get_webhook_info()

        if current_webhook.url == webhook_url and not should_force:
            logger.debug("Webhook already set for bot {}", bot.id)
            return current_webhook

        if should_force:
            logger.info("Webhook force update enabled. Set/update webhook for bot {}", bot.id)

        secret_token = self.cryptographer.generate_bot_secret(bot.id)
        webhook_request = SetWebhook(
            url=webhook_url,
            secret_token=secret_token,
            allowed_updates=allowed_updates,
            drop_pending_updates=True,
        )

        if not await bot(webhook_request):
            logger.error("Failed to set webhook for bot {}", bot.id)
            raise RuntimeError(f"Could not set webhook for bot '{bot.id}'")

        logger.info("Webhook set successfully for bot {}", bot.id)
        return await bot.get_webhook_info()

    async def remove_webhook(self, bot: Bot):
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook removed for bot {}", bot.id)
