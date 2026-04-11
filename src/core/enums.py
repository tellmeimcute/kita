from enum import StrEnum, auto


class RenderType(StrEnum):
    MESSAGE = auto()
    MEDIAGROUP = auto()


class BanAdminAction(StrEnum):
    BAN = auto()
    UNBAN = auto()
