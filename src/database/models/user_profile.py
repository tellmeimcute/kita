from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.enums import UserRole

from .abstract_model import AbstractModel
from .timestamp import TimestampMixin

if TYPE_CHECKING:
    from .user import UserAlchemy


class UserProfile(AbstractModel, TimestampMixin):
    __tablename__ = "user_profile"
    __table_args__ = (
        UniqueConstraint("bot_id", "user_id", name="uq_user_profile_bot_user"),
        Index("ix_user_profile_bot_role", "bot_id", "role"),
    )

    bot_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    prefer_anonymous: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
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

    user: Mapped["UserAlchemy"] = relationship(back_populates="profiles")

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_banned(self):
        return self.role == UserRole.BANNED
