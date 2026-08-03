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

    def to_i18n_kwargs(self) -> dict:
        data = self.model_dump(mode="json")
        updated_at = self.updated_at.strftime("%d/%m/%Y, %H:%M:%S")
        created_at = self.created_at.strftime("%d/%m/%Y, %H:%M:%S")

        data.update(updated_at=updated_at, created_at=created_at)
        return data
