from pydantic import Field

from .base import BaseConfig


class ApiRateLimitConfig(BaseConfig, env_prefix="RATELIMIT_API_"):
    enabled: bool = True
    rate: float = Field(default=25.0, gt=0)
    burst: int = Field(default=25, ge=1)
    chat_rate: float = Field(default=1.0, gt=0)
    chat_burst: int = Field(default=3, ge=1)
    flood_retries: int = Field(default=3, ge=0)
