from .base import BaseRedisRepository
from database.dto import UserDTO

class UserRedis(BaseRedisRepository[UserDTO]):
    model = UserDTO


