from pydantic import BaseModel


class UserBotStats(BaseModel):
    users_total: int
    users: int
    banned: int
    admins: int
    bot_blocked: int

    suggestions: int
    medias: int
