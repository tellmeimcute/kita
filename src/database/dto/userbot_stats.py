from pydantic import BaseModel


class UserBotStats(BaseModel):
    users_total: int
    users: int
    banned: int
    admins: int

    suggestions: int
    medias: int
