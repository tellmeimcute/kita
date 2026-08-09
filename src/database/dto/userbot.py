from pydantic import SecretStr

from core.consts import T_ME
from core.html import quote

from .base import TrackableDto


class UserBotDTO(TrackableDto):
    token: SecretStr
    bot_id: int
    username: str
    owner_id: int

    channel_id: int | None = None
    channel_name: str | None = None

    active: bool
    banned: bool

    @property
    def bot_url(self) -> str:
        return T_ME + self.username

    def to_i18n_kwargs(self) -> dict:
        data = self.model_dump(mode="json", exclude={"token"})
        data["username"] = quote(self.username)
        data["channel_name"] = quote(self.channel_name)
        return data
