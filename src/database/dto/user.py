
from typing import TYPE_CHECKING
from database.roles import UserRole
from .base import TrackableDto

if TYPE_CHECKING:
    from aiogram.types import User as AiogramUser



class UserDTO(TrackableDto):
    user_id: int
    username: str | None
    role: UserRole
    name: str
    language_code: str

    is_bot_blocked: bool | None

    def update_from_data(self, user_data: "AiogramUser"):
        new_data = {
            "name": user_data.full_name,
            "username": user_data.username,
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
