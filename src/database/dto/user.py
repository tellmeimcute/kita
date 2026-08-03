from datetime import datetime
from typing import TYPE_CHECKING

from .base import TrackableDto

if TYPE_CHECKING:
    from aiogram.types import User as AiogramUser


class UserDTO(TrackableDto):
    user_id: int
    username: str | None
    name: str
    language_code: str

    created_at: datetime | None = None
    updated_at: datetime | None = None

    def update_from_data(self, user_data: "AiogramUser"):
        new_data = {
            "name": user_data.full_name,
            "username": user_data.username,
        }

        current_data = self.model_dump(include=new_data.keys())
        for key, value in new_data.items():
            if current_data[key] != value:
                setattr(self, key, value)

    def to_i18n_kwargs(self) -> dict:
        data = self.model_dump(mode="json")
        updated_at = self.updated_at.strftime("%d/%m/%Y, %H:%M:%S")
        created_at = self.created_at.strftime("%d/%m/%Y, %H:%M:%S")

        data.update(updated_at=updated_at, created_at=created_at)
        return data
