

from database.roles import UserRole
from .base import BaseDTO

class UserDTO(BaseDTO):
    user_id: int
    username: str
    role: UserRole

    is_bot_blocked: bool | None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self) -> bool:
        return self.role == UserRole.BANNED
