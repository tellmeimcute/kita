from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.roles import UserRole

from .abstract_model import AbstractModel

if TYPE_CHECKING:
    from .suggestion import Suggestion


class UserAlchemy(AbstractModel):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column()

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="author")

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self):
        return self.role == UserRole.BANNED
