

from datetime import datetime
from pydantic import computed_field

from core.enums import RenderType
from database.enums import SuggestionStatus

from .base import TrackableDto
from .media import MediaDTO
from .user import UserDTO


class SuggestionBaseDTO(TrackableDto):
    id: int
    author_id: int
    status: SuggestionStatus

    caption: str | None
    media_group_id: str | None
    forwarded_from: str | None
    anonymous: bool = False

    created_at: datetime
    updated_at: datetime
    

class SuggestionFullDTO(SuggestionBaseDTO):
    author: UserDTO
    media: list[MediaDTO] = []

    @computed_field
    @property
    def render_type(self) -> RenderType:
        if not self.media and self.caption:
            return RenderType.MESSAGE
        return RenderType.MEDIAGROUP