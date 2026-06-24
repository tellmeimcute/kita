
from dataclasses import dataclass
from database.dto import SuggestionFullDTO
from .base import KitaEvent, UserEvent

@dataclass(frozen=True, kw_only=True, slots=True)
class NewUserEvent(UserEvent):
    ...

@dataclass(frozen=True, kw_only=True, slots=True)
class NewSuggestionEvent(KitaEvent):
    suggestion_dto: SuggestionFullDTO

@dataclass(frozen=True, kw_only=True, slots=True)
class SuggestionAcceptedEvent(KitaEvent):
    suggestion_dto: SuggestionFullDTO