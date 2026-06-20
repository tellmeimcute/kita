
from core.enums import UpperStrEnum
from enum import auto


class UserRole(UpperStrEnum):
    USER = auto()
    ADMIN = auto()
    BANNED = auto()

class SuggestionStatus(UpperStrEnum):
    PENDING = auto()
    ACCEPTED = auto()
    DECLINED = auto()