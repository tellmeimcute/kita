

from pydantic import BaseModel, field_validator

from database.roles import UserRole


class IDCommand(BaseModel):
    target_id: int

class ChangeRoleCommand(BaseModel):
    target_id: int
    target_role: UserRole

    @field_validator("target_role", mode="before")
    @classmethod
    def normalize_role(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v