

from .base import BaseRedisRepository
from database.dto import UserDTO
from core.schemas.objects import UserStats, BotInfo


class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats


class UserRedis(BaseRedisRepository[UserDTO]):
    model = UserDTO


class BotInfoRedis(BaseRedisRepository[BotInfo]):
    model = BotInfo
    expiry: int = 3600
