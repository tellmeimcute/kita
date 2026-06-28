from abc import abstractmethod
from typing import Protocol, Sequence, Any

from aiogram.types import Message
from core.schemas.objects import UserStats
from database.dto import UserDTO, SuggestionBaseDTO, SuggestionFullDTO

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

