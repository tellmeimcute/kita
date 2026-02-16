


from pydantic import BaseModel, ConfigDict
from database.roles import UserRole
from database.dto import UserDTO

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