from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel
from .timestamp import TimestampMixin

if TYPE_CHECKING:
    from .suggestion import Suggestion
    from .user_profile import UserProfile
    from .userbot import UserBot


class UserAlchemy(AbstractModel, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=False)
    language_code: Mapped[str] = mapped_column(default="ru", server_default="ru", nullable=True)

    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="author")
    bots: Mapped[list["UserBot"]] = relationship(back_populates="owner")
    profiles: Mapped[list["UserProfile"]] = relationship(back_populates="user")
