from aiogram.types import Message

from core.schemas.objects import UserStats
from database.dto import UserBotDTO, UserDTO, UserProfileDTO

from .base import BaseRedisRepository


class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats


class UserRedis(BaseRedisRepository[UserDTO]):
    model = UserDTO


class UserProfileRedis(BaseRedisRepository[UserProfileDTO]):
    model = UserProfileDTO


class UserBotRedis(BaseRedisRepository[UserBotDTO]):
    model = UserBotDTO
    _secret_fields = {"token"}
    

class TgMessageRedis(BaseRedisRepository[Message]):
    model = Message
    expiry = 15

    include = {
        "message_id",
        "from_user",
        "caption",
        "forward_origin",
        "video",
        "photo",
        "animation",
        "document",
        "media_group_id",
        "chat",
        "date",
    }
