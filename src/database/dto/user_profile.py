
from datetime import datetime
from database.enums import UserRole
from .base import TrackableDto


class UserProfileDTO(TrackableDto):
    bot_id: int
    user_id: int
    prefer_anonymous: bool = False
    is_bot_blocked: bool | None = False
    role: UserRole = UserRole.USER

    created_at: datetime
    updated_at: datetime

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self) -> bool:
        return self.role == UserRole.BANNED
