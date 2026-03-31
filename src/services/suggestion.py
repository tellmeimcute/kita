from logging import getLogger
from pydantic import BaseModel
from aiogram.types import Message, MessageOriginChannel
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, SuggestionDAO
from database.dto import SUGGESTION_DTOS, MediaDTO, SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from database.models import Media, Suggestion

from helpers.schemas.objects import UserStats
from helpers.exceptions import SQLModelNotFoundError


logger = getLogger("kita.suggestion_service")


class SuggestionService:
    dao = SuggestionDAO

    __slots__ = (
        "session",
        'config',
    )

    def __init__(self, session: AsyncSession, config: Config):
        self.session = session
        self.config = config

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

    async def set_cache(self, prefix: str, user_id: int, dataobj: BaseModel):
        key = f"{prefix}:{user_id}"
        data = dataobj.model_dump_json()
        await self.config.redis.set(
            name=key,
            value=data,
            ex=60,
        )

    async def get_cache(self, prefix: str, user_id: int, dataobj: type[BaseModel]):
        key = f"{prefix}:{user_id}"
        raw = await self.config.redis.get(key)
        if not raw:
            return None
        try:
            return dataobj.model_validate_json(raw)
        except Exception as e:
            logger.error("Fail to get %s from cache: %s", key, e, exc_info=True)
            await self.config.redis.delete(key)
            return None

    async def get_user_stats(self, user_dto: UserDTO) -> UserStats:
        stats_row = await self.get_cache("user_stats", user_dto.user_id, UserStats)
        if stats_row:
            return stats_row
        
        stats_row = await self.dao.get_stats_by_user_id(self.session, user_dto.user_id)
        user_stats = UserStats.model_validate(stats_row)

        await self.set_cache("user_stats", user_dto.user_id, user_stats)
        return user_stats

    async def get(self, suggestion_id: int, solo=False):
        dto_obj = SuggestionBaseDTO if solo else SuggestionFullDTO

        suggestion_orm = await self.dao.get_one_or_none_by_id(
            self.session, suggestion_id, solo=solo
        )

        if not suggestion_orm:
            raise SQLModelNotFoundError()

        suggestion_dto = dto_obj.model_validate(suggestion_orm)
        return suggestion_dto

    async def get_one_active(self) -> SuggestionFullDTO | None:
        active_orm = await self.dao.get_one_active(self.session)

        if not active_orm:
            raise SQLModelNotFoundError()

        active_dto = SuggestionFullDTO.model_validate(active_orm)
        return active_dto
    
    async def get_active(self) -> list[SuggestionFullDTO] | None:
        active_orm = await self.dao.get_active(self.session)

        if not active_orm:
            raise SQLModelNotFoundError()

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

    async def create_media(self, message: Message, suggestion: Suggestion):
        media_info = self._parse_media_info(message)
        if not media_info:
            return

        media_type, media_id = media_info
        media = await MediaDAO.create_from_data(
            self.session,
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

        medias: list[Media] = []

        suggestion_orm = await self.dao.create_from_data(
            self.session,
            author_id=author_dto.user_id,
            media_group_id=media_group_id,
            caption=caption,
            forwarded_from=forwarded_from,
        )
        for msg in album:
            media_orm = await self.create_media(msg, suggestion_orm)
            if media_orm:
                medias.append(media_orm)

        media_dtos = MediaDTO.from_model_list(medias)
        suggestion_base_dto = SuggestionBaseDTO.model_validate(suggestion_orm)

        suggestion_dto = SuggestionFullDTO(
            **suggestion_base_dto.model_dump(),
            author=author_dto,
            media=media_dtos,
        )

        return suggestion_dto
