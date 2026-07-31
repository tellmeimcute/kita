

from dataclasses import dataclass

from database.dto import UserDTO


@dataclass(frozen=True, kw_only=True, slots=True)
class KitaEvent:
    bot_id: int | None = None

@dataclass(frozen=True, kw_only=True, slots=True)
class UserEvent(KitaEvent):
    user_dto: UserDTO