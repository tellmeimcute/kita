from pydantic import computed_field


from database.dto.user import UserDTO
from database.dto.suggestion import SuggestionFullDTO

from .base import BaseData

class SuggestionViewerData(BaseData):
    suggestion_dtos: list[SuggestionFullDTO] | None = None
    suggestion_dto: SuggestionFullDTO | None = None
    user_dto: UserDTO

class MassMessageData(BaseData):
    users: list[UserDTO] | None = None

    is_forwarded: bool = False
    source_chat_id: int | None = None
    source_message_ids: list[int] | None = None

    progress: int = 0
    success: int = 0
    failure: int = 0

    @computed_field
    @property
    def users_count(self) -> int:
        return 0 if self.users is None else len(self.users)

    @computed_field
    @property
    def status(self) -> bool:
        return True if self.progress == self.users_count else False
