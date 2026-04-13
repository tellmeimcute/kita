from enum import StrEnum, auto

class UpperStrEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list) -> str:
        return name


class RenderType(StrEnum):
    MESSAGE = auto()
    MEDIAGROUP = auto()


class BanAdminAction(StrEnum):
    BAN = auto()
    UNBAN = auto()


class SettingsMenu(StrEnum):
    settings_menu = auto()
    settings_menu_btn = auto()
    
    locale_menu = auto()
    locale_menu_btn = auto()