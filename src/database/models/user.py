
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel

if TYPE_CHECKING:
    from .suggestion import Suggestion


class UserAlchemy(AbstractModel):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column()

    # permission: Mapped[Permission] = mapped_column()
    # balance: Mapped[int] = mapped_column()

    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="author")


