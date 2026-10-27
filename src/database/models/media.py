from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .abstract_model import AbstractModel
from .tenant import UserbotMixin

if TYPE_CHECKING:
    from .suggestion import Suggestion


class Media(AbstractModel, UserbotMixin):
    __tablename__ = "media"
    __table_args__ = (Index("ix_media_bot_id", "bot_id", "id"),)

    filetype: Mapped[str] = mapped_column()
    telegram_file_id: Mapped[str] = mapped_column()

    suggestion_id: Mapped[int] = mapped_column(ForeignKey("suggestion.id"), index=True)
    suggestion: Mapped["Suggestion"] = relationship(back_populates="media")
