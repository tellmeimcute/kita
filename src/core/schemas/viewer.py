from database.dto.suggestion import SuggestionFullDTO
from database.dto.user import UserDTO

from .base import BaseData


class SuggestionViewerData(BaseData):
    suggestion_dtos: list[SuggestionFullDTO] | None = None
    suggestion_dto: SuggestionFullDTO | None = None
    user_dto: UserDTO
