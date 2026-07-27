

from .base import BaseRedisRepository
from database.dto import UserDTO, UserProfileDTO, UserBotDTO
from core.schemas.objects import UserStats


class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats


class UserRedis(BaseRedisRepository[UserDTO]):
    model = UserDTO


class UserProfileRedis(BaseRedisRepository[UserProfileDTO]):
    model = UserProfileDTO


class UserBotRedis(BaseRedisRepository[UserBotDTO]):
    model = UserBotDTO
    expiry: int = 3600
