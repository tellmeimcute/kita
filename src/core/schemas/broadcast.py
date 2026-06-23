

from pydantic import computed_field

from database.dto.user import UserDTO

from .base import BaseData


class BroadcastData(BaseData):
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
    def is_completed(self) -> bool:
        return self.progress == self.users_count
