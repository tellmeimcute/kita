from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, BigInteger, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel
from .timestamp import TimestampMixin

if TYPE_CHECKING:
    from .user import UserAlchemy

class UserBot(AbstractModel, TimestampMixin):
    __tablename__ = "userbot"

    token: Mapped[str] = mapped_column()
    bot_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column()
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))

    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_name: Mapped[str | None] = mapped_column(nullable=True)

    active: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"), nullable=False
    )

    owner: Mapped["UserAlchemy"] = relationship(back_populates="bots")
