
from .base import BaseDTO
from .media import MediaDTO
from .user import UserDTO


class SuggestionBaseDTO(BaseDTO):
    id: int
    author_id: int

    caption: str | None
    media_group_id: str | None
    accepted: bool | None


class SuggestionFullDTO(SuggestionBaseDTO):
    author: UserDTO
    media: list[MediaDTO] = []
