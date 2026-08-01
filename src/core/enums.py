from enum import StrEnum, auto


class UpperStrEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list) -> str:
        return name


class RenderType(StrEnum):
    MESSAGE = auto()
    MEDIAGROUP = auto()
