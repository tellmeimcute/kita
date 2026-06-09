from .base import BaseRedisRepository
from core.schemas.objects import UserStats

class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats