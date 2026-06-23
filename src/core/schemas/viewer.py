

from .base import BaseData

from database.dto.user import UserDTO
from database.dto.suggestion import SuggestionFullDTO


class SuggestionViewerData(BaseData):
    suggestion_dtos: list[SuggestionFullDTO] | None = None
    suggestion_dto: SuggestionFullDTO | None = None
    user_dto: UserDTO
