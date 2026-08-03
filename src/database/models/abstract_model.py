from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class AbstractModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: PLW3201
        return cls.__name__.lower()

    def __repr__(self) -> str:
        insp = inspect(self)
        attr_str = ", ".join(
            f"{col.key}={getattr(self, col.key, 'N/A')}" for col in insp.mapper.column_attrs
        )
        return f"{self.__class__.__name__}({attr_str})"
