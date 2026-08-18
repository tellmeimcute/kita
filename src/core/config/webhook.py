from pydantic import SecretStr

from .base import BaseConfig


class WebhookConfig(BaseConfig, env_prefix="WEBHOOK_"):
    domain: SecretStr
    port: int = 8443

    path: str = "/webhook"
    force_update: bool = False

    max_concurrent_updates: int = 50
