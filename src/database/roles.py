


from enum import Enum, StrEnum, auto


class UpperStrEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list) -> str:
        return name

class UserRole(UpperStrEnum):
    USER = auto()
    ADMIN = auto()
    BANNED = auto()
