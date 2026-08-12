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

    @property
    def shifted_channel_id(self) -> int:
        """
        Returns shifted chat ID (positive and without "-100" prefix).
        Mostly used for private links like t.me/c/chat_id/message_id

        Currently supergroup/channel IDs have 10-digit ID after "-100" prefix removed.
        However, these IDs might become 11-digit in future. So, first we remove "-100"
        prefix and count remaining number length. Then we multiple
        -1 * 10 ^ (number_length + 2)
        Finally, self.id is substracted from that number
        """
        short_id = str(self.channel_id).replace("-100", "")
        shift = int(-1 * pow(10, len(short_id) + 2))
        return shift - self.channel_id

    def to_i18n_kwargs(self) -> dict:
        data = self.model_dump(mode="json", exclude={"token"})
        data["username"] = quote(self.username)
        data["channel_name"] = quote(self.channel_name)
        return data
