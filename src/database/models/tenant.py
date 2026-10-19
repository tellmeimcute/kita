from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column


class UserbotMixin:
    bot_id: Mapped[int] = mapped_column(BigInteger)
