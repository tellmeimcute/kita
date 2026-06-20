
from typing import Any
from logging import getLogger
from dataclasses import asdict

from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import SQLSuggestionNotFoundError, UnsupportedPayload
from core.schemas.objects import UserStats

from database.repository import SuggestionRepository
from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from database.models import Media, Suggestion
from database.redis.userstats import UserStatsRedis

from services.message_parser import MessageParser

logger = getLogger("kita.suggestion_service")


class SuggestionService:

    __slots__ = (
        "session",
        "redis",
        "redis_key",
        "repo",
        "parser",
    )

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        repo: SuggestionRepository,
        parser: MessageParser,
    ):
        self.session = session
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
        dto = await self.repo.get_by_id(suggestion_id)
        if not dto:
            raise SQLSuggestionNotFoundError(suggestion_id)
        return dto

    async def get_active(self) -> list[SuggestionFullDTO]:
        dtos = await self.repo.get_active()
        if not dtos:
            raise SQLSuggestionNotFoundError()
        return dtos

    async def update(self, suggestion_dto: SuggestionBaseDTO):
        await self.repo.save(suggestion_dto)
        logger.info("Update suggestion %s", suggestion_dto.id)

    async def update_by_id(self, suggestion_id: int, **data: Any):
        await self.repo.update(suggestion_id, **data)
        logger.info("Update suggestion %s", suggestion_id)

    async def create(self, author_dto: UserDTO, album: list[Message]) -> SuggestionFullDTO:
        first_msg = album[0]

        media_group_id = first_msg.media_group_id
        caption = first_msg.caption or first_msg.text
        forwarded_from = self.parser.parse_forward_origin(first_msg)
        
        suggestion_orm = Suggestion(
            author_id=author_dto.user_id,
            media_group_id=media_group_id,
            caption=caption,
            forwarded_from=forwarded_from,
            anonymous=author_dto.prefer_anonymous,
        )

        for msg in album:
            if media_info := self.parser.parse_media(msg):
                suggestion_orm.media.append(Media(**asdict(media_info)))

        if not suggestion_orm.caption and not suggestion_orm.media:
            raise UnsupportedPayload()

        self.session.add(suggestion_orm)
        await self.session.flush()
        await self.session.refresh(suggestion_orm, attribute_names=["media", "author"])
        return SuggestionFullDTO.model_validate(suggestion_orm)
    