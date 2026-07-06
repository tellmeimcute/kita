from abc import abstractmethod
from typing import Protocol, Sequence, Any

from aiogram.types import Message, InlineKeyboardMarkup
from core.schemas.objects import UserStats
from core.schemas.message_payload import MessagePayload
from database.dto import UserDTO, SuggestionBaseDTO, SuggestionFullDTO
from ui.senders.base import BaseSender


class UserServiceProtocol(Protocol):

    @abstractmethod
    async def get(self, user_id: int) -> UserDTO | None:
        ...

    @abstractmethod
    async def create(self, prep_user_dto: UserDTO) -> UserDTO:
        ...

    @abstractmethod
    async def update(self, user_id: int, **data: Any) -> None:
        ...

    @abstractmethod
    async def save(self, user_dto: UserDTO) -> None:
        ...

    @abstractmethod
    async def get_active(self): ...

    @abstractmethod
    async def get_admins(self): ...


class SuggestionServiceProtocol(Protocol):

    @abstractmethod
    async def get(self, suggestion_id: int) -> SuggestionFullDTO:
        ...

    @abstractmethod
    async def get_active(self) -> Sequence[SuggestionFullDTO]:
        ...

    @abstractmethod
    async def create(self, author_dto: UserDTO, album: Sequence[Message]) -> SuggestionFullDTO:
        ...

    @abstractmethod
    async def update(self, suggestion_dto: SuggestionBaseDTO) -> None:
        ...

    @abstractmethod
    async def update_by_id(self, suggestion_id: int, **data: Any) -> None:
        ...

    @abstractmethod
    async def get_user_stats(self, user_dto: UserDTO) -> UserStats:
        ...


class NotifierServiceProtocol:

    @abstractmethod
    def strategy_factory(
        self, target_id: int, payload: MessagePayload, silent: bool = True
    ) -> BaseSender: ...

    @abstractmethod
    async def notify_user(self, user_dto: UserDTO, payload: MessagePayload): ...

    @abstractmethod
    async def forward_messages(self, user_dto: UserDTO, messages: list[int], source: int): ...

    @abstractmethod
    async def copy_messages(self, user_dto: UserDTO, messages: list[int], source: int): ...

    @abstractmethod
    async def edit_message_text(
        self,
        message: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ): ...
