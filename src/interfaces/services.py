from collections.abc import Sequence
from typing import Any, Protocol

from aiogram import Bot
from aiogram.types import Message, WebhookInfo
from aiogram_dialog import DialogManager

from core.schemas.objects import UserStats
from database.dto import (
    SuggestionBaseDTO,
    SuggestionFullDTO,
    UserBotDTO,
    UserDTO,
    UserProfileDTO,
)
from database.enums import UserRole


class UserServiceProtocol(Protocol):
    async def get(self, user_id: int) -> UserDTO | None: ...

    async def create(self, prep_user_dto: UserDTO) -> UserDTO: ...

    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO: ...

    async def update(self, user_id: int, **data: Any) -> None: ...

    async def save(self, user_dto: UserDTO) -> None: ...


class UserProfileServiceProtocol(Protocol):
    async def get_or_create(self, user_id: int) -> UserProfileDTO: ...

    async def create(self, user_id: int) -> UserProfileDTO: ...

    async def get(self, user_id: int) -> UserProfileDTO | None: ...

    async def get_many(
        self,
        limit: int = 10,
        offset: int = 0,
        order_desc: bool = False,
        role: UserRole | None = None,
        bot_blocked: bool | None = None,
    ): ...

    async def update(self, user_id: int, **data: Any) -> None: ...

    async def save(self, profile_dto: UserProfileDTO) -> None: ...

    async def get_active(self) -> Sequence[UserProfileDTO]: ...

    async def get_admins(self) -> Sequence[UserProfileDTO]: ...

    async def demote_admins(self, owner_id: int) -> int: ...

    async def decline_suggestion(self, profile_dto: UserProfileDTO) -> None: ...


class SuggestionServiceProtocol(Protocol):
    async def get(self, suggestion_id: int) -> SuggestionFullDTO: ...

    async def get_active(self) -> Sequence[SuggestionFullDTO]: ...

    async def create(
        self, author_dto: UserDTO, album: Sequence[Message], anonymous: bool = False
    ) -> SuggestionFullDTO: ...

    async def update(self, suggestion_dto: SuggestionBaseDTO) -> None: ...

    async def update_by_id(self, suggestion_id: int, **data: Any) -> None: ...

    async def get_user_stats(self, user_dto: UserDTO) -> UserStats: ...


class SuggestionQueueProtocol(Protocol):
    async def seed_queue(self, suggestions: Sequence[SuggestionFullDTO]) -> list[dict]: ...

    async def next_suggestion(self) -> SuggestionFullDTO | None: ...


class SuggestionViewerProtocol(Protocol):
    async def advance(self, user_dto: UserDTO) -> bool: ...

    async def get_current(self) -> SuggestionFullDTO | None: ...

    async def return_to_menu(self, manager: DialogManager, user_dto: UserDTO): ...


class UserBotServiceProtocol(Protocol):
    async def get(self, bot_id: int) -> UserBotDTO | None: ...

    async def get_active(self) -> Sequence[UserBotDTO]: ...

    async def get_by_owner_id(self, owner_id: int) -> Sequence[UserBotDTO]: ...

    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ) -> None: ...

    async def update(self, bot_id: int, **data: Any) -> None: ...

    async def save(self, userbot_dto: UserBotDTO) -> None: ...


class WebhookServiceProtocol(Protocol):
    async def set_webhook(
        self,
        bot: Bot,
        url: str | None = None,
        force_update: bool = False,
        allowed_updates: Sequence[str] | None = None,
    ) -> WebhookInfo: ...

    async def remove_webhook(self, bot: Bot) -> None: ...
