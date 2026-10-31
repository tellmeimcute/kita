from pydantic import Field

from .base import BaseConfig


class RateLimitConfig(BaseConfig, env_prefix="RATELIMIT_"):
    max_tokens: int = Field(default=10, gt=0)
    refill_rate: float = Field(default=1.0, gt=0)
