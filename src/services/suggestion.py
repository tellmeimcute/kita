
from logging import getLogger
from aiogram.types import Message, MessageOriginChannel
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from database.models import Suggestion, Media
from database.dao import SuggestionDAO
from database.redis.userstats import UserStatsRedis
from database.dto import (
    SUGGESTION_DTOS,
    MediaDTO,
    SuggestionBaseDTO,
    SuggestionFullDTO,
    UserDTO,
)
from database.models import Media, Suggestion
from helpers.schemas.objects import UserStats
from core.exceptions import SQLSuggestionNotFoundError, UnsupportedPayload


logger = getLogger("kita.suggestion_service")


class SuggestionService:
    dao = SuggestionDAO

    __slots__ = (
        "session",
        'config',
        "redis",
    )

    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis

    def _parse_media_info(self, message: Message) -> tuple[str, str] | None:
        if message.video:
            return "video", message.video.file_id
        elif message.photo:
            return "photo", message.photo[-1].file_id
        elif message.animation:
            return "document", message.animation.file_id
        elif message.document:
            return "document", message.document.file_id
        return None

    def _parse_origin_info(self, message: Message):
        origin = message.forward_origin
        if isinstance(origin, MessageOriginChannel):
            return origin.chat.full_name
        return None

    async def get_user_stats(self, user_dto: UserDTO) -> UserStats:
        key = f"user_stats:{user_dto.user_id}"

        stats_row = await UserStatsRedis.get(self.redis, key)
        if stats_row:
            return stats_row
        
        stats_row = await self.dao.get_stats_by_user_id(self.session, user_dto.user_id)
        user_stats = UserStats.model_validate(stats_row)

        stats_row = await UserStatsRedis.set(self.redis, key, user_stats)
        return user_stats

    async def get(self, suggestion_id: int, solo=False):
        dto_obj = SuggestionBaseDTO if solo else SuggestionFullDTO

        suggestion_orm = await self.dao.get_one_or_none_by_id(
            self.session, suggestion_id, solo=solo
        )

        if not suggestion_orm:
            raise SQLSuggestionNotFoundError(target_id=suggestion_id)

        suggestion_dto = dto_obj.model_validate(suggestion_orm)
        return suggestion_dto

    async def get_active(self) -> list[SuggestionFullDTO] | None:
        active_orm = await self.dao.get_active(self.session)

        if not active_orm:
            raise SQLSuggestionNotFoundError()

        active_dtos = SuggestionFullDTO.from_model_list(active_orm)
        return active_dtos

    async def update(self, suggestion_dto: SUGGESTION_DTOS):
        changed_data = suggestion_dto.prepare_changed_data()
        if not changed_data:
            return

        await self.dao.update_by_id(self.session, suggestion_dto.id, changed_data)

        logger.info(
            "Update database info for suggestion %s. New data: %s", suggestion_dto.id, changed_data
        )

    def create_media(self, message: Message, suggestion: Suggestion):
        media_info = self._parse_media_info(message)
        if not media_info:
            return

        media_type, media_id = media_info

        media = Media(
            filetype=media_type,
            telegram_file_id=media_id,
            suggestion=suggestion,
        )

        return media

    async def create(self, author_dto: UserDTO, album: list[Message]) -> SuggestionFullDTO:
        first_msg = album[0]

        media_group_id = first_msg.media_group_id
        caption = first_msg.caption or first_msg.text
        forwarded_from = self._parse_origin_info(first_msg)

        suggestion_orm = Suggestion(
            author_id=author_dto.user_id,
            media_group_id=media_group_id,
            caption=caption,
            forwarded_from=forwarded_from,
        )

        media_list = []

        for msg in album:
            media_orm = self.create_media(msg, suggestion_orm)
            if media_orm:
                media_list.append(media_orm)

        to_add = [suggestion_orm] + media_list

        if not suggestion_orm.caption and not media_list:
            raise UnsupportedPayload()

        self.session.add_all(to_add)
        await self.session.flush(to_add)
        await self.session.commit()

        media_dtos = MediaDTO.from_model_list(media_list)
        suggestion_base_dto = SuggestionBaseDTO.model_validate(suggestion_orm)

        suggestion_dto = SuggestionFullDTO(
            **suggestion_base_dto.model_dump(),
            author=author_dto,
            media=media_dtos,
        )

        return suggestion_dto
