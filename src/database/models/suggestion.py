from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel
from .timestamp import TimestampMixin

if TYPE_CHECKING:
    from .media import Media
    from .user import UserAlchemy


class Suggestion(AbstractModel, TimestampMixin):
    __tablename__ = "suggestion"

    caption: Mapped[str | None] = mapped_column(nullable=True)
    media_group_id: Mapped[str | None] = mapped_column(nullable=True, default=None)
    forwarded_from: Mapped[str | None] = mapped_column(nullable=True, default=None)

    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)

    anonymous: Mapped[bool] = mapped_column(default=False, server_default=text("false"), nullable=False)

    # None если еще не рассмотрено.
    accepted: Mapped[bool | None] = mapped_column(nullable=True, default=None, index=True)

    author: Mapped["UserAlchemy"] = relationship(back_populates="suggestions")
    media: Mapped[list["Media"]] = relationship(back_populates="suggestion")
