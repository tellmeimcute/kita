from collections.abc import Sequence
from logging import getLogger

from aiogram import Bot
from aiogram.methods import SetWebhook
from aiogram.types import WebhookInfo

from core.config import Config
from core.cryptographer import Cryptographer
from interfaces import BotRegistryProtocol

logger = getLogger("kita.webhook")


class WebhookService:
    def __init__(self, config: Config, bot_registry: BotRegistryProtocol):
        self.config = config
        self.bot_registry = bot_registry
        self.cryptographer = Cryptographer(config)

    async def set_webhook(
        self,
        bot: Bot,
        url: str | None = None,
        force_update: bool = False,
        allowed_updates: Sequence[str] | None = None,
    ) -> WebhookInfo:
        webhook_url = url or f"{self.config.webhook_base_url}/{bot.id}"
        should_force = force_update or self.config.webhook_force_update
        current_webhook = await bot.get_webhook_info()

        if current_webhook.url == webhook_url and not should_force:
            logger.debug("Webhook already set for bot %s: %s", bot.id, webhook_url)
            return current_webhook

        if should_force:
            logger.info("Webhook force update enabled. Set/update webhook for bot %s", bot.id)

        secret_token = self.cryptographer.generate_bot_secret(bot.id)
        webhook_request = SetWebhook(
            url=webhook_url,
            secret_token=secret_token,
            allowed_updates=allowed_updates or self.bot_registry.allowed_updates,
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
