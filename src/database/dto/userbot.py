
from pydantic import SecretStr
from .base import TrackableDto


class UserBotDTO(TrackableDto):
    token: SecretStr
    bot_id: int
    username: str
    owner_id: int

    channel_id: int | None = None
    channel_name: str | None = None

    active: bool
