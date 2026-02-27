

from database.roles import UserRole
from .base import TrackableDto

class UserDTO(TrackableDto):
    user_id: int
    username: str | None
    role: UserRole
    name: str

    is_bot_blocked: bool | None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self) -> bool:
        return self.role == UserRole.BANNED
