
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel
if TYPE_CHECKING:
    from .suggestion import Suggestion


class Media(AbstractModel):
    __tablename__ = "media"

    filetype: Mapped[str] = mapped_column()
    telegram_file_id: Mapped[str] = mapped_column()

    suggestion_id: Mapped[int] = mapped_column(ForeignKey("suggestion.id"))
    suggestion: Mapped["Suggestion"] = relationship(back_populates="media")