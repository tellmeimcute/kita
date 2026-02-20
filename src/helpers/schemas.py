from pydantic import BaseModel, ConfigDict

from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO
from database.roles import UserRole
from helpers.enums import RenderType
from services.notifier import Notifier


class ChangeRoleCommand(BaseModel):
    target_id: int
    target_role: UserRole

    caller_dto: UserDTO
    notifier: Notifier

    bot_owner_id: int

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class IDCommand(BaseModel):
    target_id: int


class SuggestionViewerData(BaseModel):
    suggestion_dto: SuggestionBaseDTO | SuggestionFullDTO
    user_dto: UserDTO
    channel_id: int
    
    render_type: RenderType | None = None

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )