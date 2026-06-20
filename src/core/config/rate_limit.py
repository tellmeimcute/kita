
from .base import BaseConfig


class RateLimitConfig(BaseConfig, env_prefix="RATELIMIT_"):
    max_tokens: int = 10
    refill_rate: float = 1.0