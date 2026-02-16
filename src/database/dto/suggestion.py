from pydantic import BaseModel, ConfigDict

from .media import MediaDTO
from .user import UserDTO


class SuggestionBaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int

    caption: str | None
    media_group_id: str | None
    accepted: bool | None


class SuggestionFullDTO(SuggestionBaseDTO):
    author: UserDTO
    media: list[MediaDTO] = []
