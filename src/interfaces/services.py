from abc import abstractmethod
from collections.abc import Sequence
from typing import Any, Protocol

from aiogram.types import Message

from core.schemas.objects import UserStats
from database.dto import SuggestionBaseDTO, SuggestionFullDTO, UserDTO, UserProfileDTO


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
    async def get_many(self, limit: int = 10, offset: int = 0, order_desc: bool = False): ...

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
