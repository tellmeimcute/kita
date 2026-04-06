from .base import BaseData


class UserData(BaseData):
    id: int
    full_name: str
    username: str | None = None

class UserStats(BaseData):
    total: int
    accepted: int
    declined: int