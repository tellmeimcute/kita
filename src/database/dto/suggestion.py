

from pydantic import computed_field
from helpers.enums import RenderType

from .base import TrackableDto
from .media import MediaDTO
from .user import UserDTO


class SuggestionBaseDTO(TrackableDto):
    id: int
    author_id: int

    caption: str | None
    media_group_id: str | None
    forwarded_from: str | None

    accepted: bool | None


class SuggestionFullDTO(SuggestionBaseDTO):
    author: UserDTO
    media: list[MediaDTO] = []

    @computed_field
    @property
    def render_type(self) -> RenderType:
        if not self.media and self.caption:
            return RenderType.MESSAGE
        return RenderType.MEDIAGROUP

SUGGESTION_DTOS = SuggestionFullDTO | SuggestionBaseDTO
