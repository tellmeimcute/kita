
from .base import BaseDTO
from .media import MediaDTO
from .user import UserDTO
from .base import TrackableDto

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
