

from pydantic import Field

from .base import BaseData


class IDCommand(BaseData):
    target_id: int = Field(ge=1, le=9_223_372_036_854_775_807)
