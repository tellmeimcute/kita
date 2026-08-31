from aiogram.types import Message
from pydantic import TypeAdapter

from core.schemas.objects import UserStats
from database.dto import (
    UserBotDTO,
    UserBotStats,
    UserDTO,
    UserProfileDTO,
)

from .base import BaseRedisRepository


class IntRedis(BaseRedisRepository[int]):
    adapter = TypeAdapter(int)
    expiry = 30


class UserStatsRedis(BaseRedisRepository[UserStats]):
    model = UserStats


class UserBotStatsRedis(BaseRedisRepository[UserBotStats]):
    model = UserBotStats
    expiry = 30


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
