from pydantic import BaseModel

class RuntimeConfig(BaseModel):
    channel_name: str
    bot_username: str
    bot_url: str