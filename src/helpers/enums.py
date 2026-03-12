from enum import StrEnum, auto

class BoolAction(StrEnum):
    ACCEPT = auto()
    DECLINE = auto()

class RenderType(StrEnum):
    MESSAGE = auto()
    MEDIAGROUP = auto()

class ViewerAdminAction(StrEnum):
    ACCEPT = auto()
    DECLINE = auto()
    ACCEPT_NO_CAPTION = auto()

class BanAdminAction(StrEnum):
    BAN = auto()
    UNBAN = auto()
