
from pydantic import BaseModel, Field

class IDCommand(BaseModel):
    target_id: int = Field(ge=-9_223_372_036_854_775_808, le=9_223_372_036_854_775_807)
