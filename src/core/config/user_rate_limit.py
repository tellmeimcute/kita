from pydantic import Field

from .base import BaseConfig


class UserRateLimitConfig(BaseConfig, env_prefix="RATELIMIT_USER_"):
    max_tokens: int = Field(default=10, gt=0)
    refill_rate: float = Field(default=1.0, gt=0)
