from .base import BaseRedisRepository
from helpers.schemas.objects import UserStats

class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats