from abc import abstractmethod
from collections.abc import Sequence
from typing import Any, Literal, Protocol

from aiogram.types import InlineKeyboardMarkup, Message, MessageId

from core.schemas.message_payload import MessagePayload
from core.schemas.objects import UserStats
from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO, UserProfileDTO
from ui.senders.base import BaseSender


class UserServiceProtocol(Protocol):
    @abstractmethod
    async def get(self, user_id: int) -> UserDTO | None: ...

    @abstractmethod
    async def create(self, prep_user_dto: UserDTO) -> UserDTO: ...

    @abstractmethod
    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO: ...

    @abstractmethod
    async def update(self, user_id: int, **data: Any) -> None: ...

    @abstractmethod
    async def save(self, user_dto: UserDTO) -> None: ...


class UserProfileServiceProtocol(Protocol):
    @abstractmethod
    async def get_or_create(self, user_id: int) -> UserProfileDTO: ...

    @abstractmethod
    async def create(self, user_id: int) -> UserProfileDTO: ...

    @abstractmethod
    async def get(self, user_id: int) -> UserProfileDTO | None: ...

    @abstractmethod
    async def get_many(self, limit: int = 10, offset: int = 0): ...

    @abstractmethod
    async def update(self, user_id: int, **data: Any) -> None: ...

    @abstractmethod
    async def save(self, profile_dto: UserProfileDTO) -> None: ...

    @abstractmethod
    async def get_active(self) -> Sequence[UserProfileDTO]: ...

    @abstractmethod
    async def get_admins(self) -> Sequence[UserProfileDTO]: ...

    @abstractmethod
    async def decline_suggestion(self, profile_dto: UserProfileDTO) -> None: ...


class SuggestionServiceProtocol(Protocol):
    @abstractmethod
    async def get(self, suggestion_id: int) -> SuggestionFullDTO: ...

    @abstractmethod
    async def get_active(self) -> Sequence[SuggestionFullDTO]: ...

    @abstractmethod
    async def create(
        self, author_dto: UserDTO, album: Sequence[Message], anonymous: bool = False
    ) -> SuggestionFullDTO: ...

    @abstractmethod
    async def update(self, suggestion_dto: SuggestionBaseDTO) -> None: ...

    @abstractmethod
    async def update_by_id(self, suggestion_id: int, **data: Any) -> None: ...

    @abstractmethod
    async def get_user_stats(self, user_dto: UserDTO) -> UserStats: ...


class NotifierServiceProtocol:
    @abstractmethod
    def strategy_factory(
        self, target_id: int, payload: MessagePayload, silent: bool = True
    ) -> BaseSender: ...

    @abstractmethod
    async def send_suggestion(
        self,
        target: UserDTO | int,
        dto: SuggestionFullDTO,
        mode: Literal["admin_viewer", "channel_post"] = "admin_viewer",
    ) -> Message | list[Message] | None: ...

    @abstractmethod
    async def send_text(
        self,
        target: UserDTO | int,
        i18n_key: str,
        i18n_kwargs: dict | None = None,
        kb: Any | None = None,
    ): ...

    @abstractmethod
    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload): ...

    @abstractmethod
    async def forward_messages(
        self, user_dto: UserDTO, messages: list[int], source: int
    ) -> list[MessageId]: ...

    @abstractmethod
    async def copy_messages(
        self, user_dto: UserDTO, messages: list[int], source: int
    ) -> list[MessageId]: ...

    @abstractmethod
    async def edit_message_text(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ): ...
