from .base import BaseData

class UserStats(BaseData):
    total: int
    accepted: int
    declined: int


class BotInfo(BaseData):
    bot_id: int
    
    channel_name: str
    bot_username: str
    bot_url: str