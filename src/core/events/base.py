

from dataclasses import dataclass
from dishka import AsyncContainer
from database.dto import UserDTO

@dataclass(frozen=True, kw_only=True, slots=True)
class KitaEvent:
    container: AsyncContainer | None = None

@dataclass(frozen=True, kw_only=True, slots=True)
class UserEvent(KitaEvent):
    user_dto: UserDTO