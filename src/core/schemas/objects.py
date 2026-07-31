from dataclasses import dataclass

from .base import BaseData


class UserStats(BaseData):
    total: int
    accepted: int
    declined: int


@dataclass
class MediaInfo:
    filetype: str
    telegram_file_id: str
