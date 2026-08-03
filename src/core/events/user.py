from dataclasses import dataclass

from database.dto import SuggestionFullDTO, UserDTO

from .base import KitaEvent, UserEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class NewUserEvent(UserEvent): ...


@dataclass(frozen=True, kw_only=True, slots=True)
class CopyMessagesToUserEvent(UserEvent):
    caller_dto: UserDTO
    source_chat_id: int
    album_ids: list[int]


@dataclass(frozen=True, kw_only=True, slots=True)
class NewSuggestionEvent(KitaEvent):
    suggestion_dto: SuggestionFullDTO


@dataclass(frozen=True, kw_only=True, slots=True)
class SuggestionAcceptedEvent(KitaEvent):
    suggestion_dto: SuggestionFullDTO
