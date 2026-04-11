from pydantic import BaseModel, Field, field_validator

from database.roles import UserRole


class IDCommand(BaseModel):
    target_id: int = Field(ge=-9_223_372_036_854_775_808, le=9_223_372_036_854_775_807)


class StrCommand(BaseModel):
    string: str


class ChangeRoleCommand(IDCommand):
    target_role: UserRole

    @field_validator("target_role", mode="before")
    @classmethod
    def normalize_role(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v
