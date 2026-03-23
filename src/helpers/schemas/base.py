

from pydantic import BaseModel, ConfigDict


class BaseData(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )