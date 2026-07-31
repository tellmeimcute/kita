
from pydantic import SecretStr

from core.consts import T_ME

from .base import TrackableDto


class UserBotDTO(TrackableDto):
    token: SecretStr
    bot_id: int
    username: str
    owner_id: int

    channel_id: int | None = None
    channel_name: str | None = None

    active: bool

    @property
    def bot_url(self) -> str:
        return T_ME + self.username
    