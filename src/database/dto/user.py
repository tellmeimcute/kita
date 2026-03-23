from aiogram.types import User as UserTelegram

from database.roles import UserRole

from .base import TrackableDto


class UserDTO(TrackableDto):
    user_id: int
    username: str | None
    role: UserRole
    name: str

    is_bot_blocked: bool | None

    def update_from_tg(self, user_tg: UserTelegram):
        new_data = {
            "name": user_tg.full_name,
            "username": user_tg.username,
        }

        current_data = self.model_dump(include=new_data.keys())
        for key, value in new_data.items():
            if current_data[key] != value:
                setattr(self, key, value)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self) -> bool:
        return self.role == UserRole.BANNED
