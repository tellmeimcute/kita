from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.roles import UserRole

from .abstract_model import AbstractModel
from .timestamp import TimestampMixin

if TYPE_CHECKING:
    from .suggestion import Suggestion


class UserAlchemy(AbstractModel, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=False)

    is_bot_blocked: Mapped[bool] = mapped_column(default=False, nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            create_constraint=True,
            validate_strings=True,
        ),
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
