from pydantic import BaseModel, ConfigDict

from database.dto import SuggestionFullDTO, UserDTO
from database.roles import UserRole
from helpers.enums import RenderType
from services.notifier import Notifier


class ChangeRoleData(BaseModel):
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

class SuggestionViewerData(BaseModel):
    suggestion_dto: SuggestionFullDTO
    user_dto: UserDTO
    channel_id: int
    
    render_type: RenderType | None = None

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )