

from database.dto import UserDTO, MediaDTO
from .base import BaseData


class SuggestionData(BaseData):
    caption: str | None
    media_group_id: str | None
    forwarded_from: str | None

    author: UserDTO | None
    media: list[MediaDTO] | None

    accepted: bool | None

class UserData(BaseData):
    id: int
    full_name: str
    username: str | None = None
