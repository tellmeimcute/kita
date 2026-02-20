from enum import StrEnum, auto


class RenderType(StrEnum):
    MESSAGE = auto()
    MEDIAGROUP = auto()


class ViewerAdminAction(StrEnum):
    ACCEPT = auto()
    DECLINE = auto()
    ACCEPT_NO_CAPTION = auto()

