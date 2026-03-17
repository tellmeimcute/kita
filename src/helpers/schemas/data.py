from pydantic import BaseModel, ConfigDict, computed_field

from aiogram.types import ReplyKeyboardMarkup

from database.dto import SuggestionFullDTO, UserDTO
from database.roles import UserRole
from helpers.enums import RenderType
from services.notifier import Notifier

class BaseData(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ChangeRoleData(BaseData):
    target_id: int
    target_role: UserRole

    caller_dto: UserDTO
    notifier: Notifier

    target_new_kb: ReplyKeyboardMarkup | None = None

class SuggestionViewerData(BaseData):
    suggestion_dto: SuggestionFullDTO
    user_dto: UserDTO
    channel_id: int
    
    render_type: RenderType | None = None

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