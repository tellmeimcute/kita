from pydantic import BaseModel, ConfigDict

from database.roles import UserRole


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self) -> bool:
        return self.role == UserRole.BANNED
