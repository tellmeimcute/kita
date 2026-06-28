
from typing import Any
from logging import getLogger

from aiogram.types import Message
from redis.asyncio import Redis

from core.consts import SUGGESTION_CAPTION_LIMIT, SUGGESTION_TEXT_LIMIT
from core.exceptions import UnsupportedPayload
from core.schemas.objects import UserStats

from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from database.redis.userstats import UserStatsRedis
from interfaces import SuggestionRepositoryProtocol

from services.message_parser import MessageParser

logger = getLogger("kita.suggestion_service")


class SuggestionService:

    __slots__ = (
        "redis",
        "redis_key",
        "repo",
        "parser",
    )

    def __init__(
        self,
        redis: Redis,
        repo: SuggestionRepositoryProtocol,
        parser: MessageParser,
    ):
        self.redis = redis
        self.redis_key = lambda x: f"user_stats:{x}"
        self.repo = repo
        self.parser = parser
        
    async def get_user_stats(self, user_dto: UserDTO) -> UserStats:
        key = self.redis_key(user_dto.user_id)

        stats_row = await UserStatsRedis.get(self.redis, key)
        if stats_row:
            return stats_row
        
        user_stats = await self.repo.get_user_stats(user_dto.user_id)
        await UserStatsRedis.set(self.redis, key, user_stats)
        return user_stats

    async def get(self, suggestion_id: int):
        return await self.repo.get_by_id(suggestion_id)

    async def get_active(self) -> list[SuggestionFullDTO]:
        return await self.repo.get_active()

    async def update(self, suggestion_dto: SuggestionBaseDTO):
        await self.repo.save(suggestion_dto)
        logger.info("Update suggestion %s", suggestion_dto.id)

    async def update_by_id(self, suggestion_id: int, **data: Any):
        await self.repo.update(suggestion_id, **data)
        logger.info("Update suggestion %s", suggestion_id)

    async def create(self, author_dto: UserDTO, album: list[Message]) -> SuggestionFullDTO:
        first_msg = album[0]
        caption = first_msg.caption or first_msg.text
        media_group_id = first_msg.media_group_id
        forwarded_from = self.parser.parse_forward_origin(first_msg)
        media_info = [
            info for msg in album 
            if (info := self.parser.parse_media(msg))
        ]

        if not caption and not media_info:
            raise UnsupportedPayload
        if caption and media_info and len(caption) > SUGGESTION_CAPTION_LIMIT:
            raise UnsupportedPayload
        if caption and not media_info and len(caption) > SUGGESTION_TEXT_LIMIT:
            raise UnsupportedPayload

        return await self.repo.create(
            author_id=author_dto.user_id,
            anonymous=author_dto.prefer_anonymous,
            mediainfo=media_info,
            caption=caption,
            media_group_id=media_group_id,
            forwarded_from=forwarded_from,
        )