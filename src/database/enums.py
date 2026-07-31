
from enum import auto

from core.enums import UpperStrEnum


class UserRole(UpperStrEnum):
    USER = auto()
    ADMIN = auto()
    BANNED = auto()

class SuggestionStatus(UpperStrEnum):
    PENDING = auto()
    ACCEPTED = auto()
    DECLINED = auto()