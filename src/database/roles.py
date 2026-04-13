
from core.enums import UpperStrEnum
from enum import auto


class UserRole(UpperStrEnum):
    USER = auto()
    ADMIN = auto()
    BANNED = auto()
