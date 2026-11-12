from dataclasses import dataclass

from .base import Event


@dataclass(frozen=True, slots=True)
class SuggestionCreated(Event):
    suggestion_id: int


@dataclass(frozen=True, slots=True)
class SuggestionAccepted(Event):
    suggestion_id: int


@dataclass(frozen=True, slots=True)
class SuggestionDeclined(Event):
    suggestion_id: int


@dataclass(frozen=True, slots=True)
class UserRegistered(Event):
    user_id: int


@dataclass(frozen=True, slots=True)
class UserProfileCreated(Event):
    """A profile of ``user_id`` was created for the bot ``bot_id``."""

    user_id: int


@dataclass(frozen=True, slots=True)
class UserbotRegistered(Event):
    userbot_id: int
    owner_id: int


@dataclass(frozen=True, slots=True)
class UserbotActivated(Event):
    userbot_id: int
    owner_id: int


@dataclass(frozen=True, slots=True)
class UserbotDeactivated(Event):
    userbot_id: int
    owner_id: int
