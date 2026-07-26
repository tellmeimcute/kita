

from .base import BaseRedisRepository
from database.dto import UserDTO, UserProfileDTO, UserBotDTO
from core.schemas.objects import UserStats, BotInfo


class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats


class UserRedis(BaseRedisRepository[UserDTO]):
    model = UserDTO


class UserProfileRedis(BaseRedisRepository[UserProfileDTO]):
    model = UserProfileDTO


class BotInfoRedis(BaseRedisRepository[BotInfo]):
    model = BotInfo
    expiry: int = 3600

class UserBotRedis(BaseRedisRepository[UserBotDTO]):
    model = UserBotDTO
    expiry: int = 3600
