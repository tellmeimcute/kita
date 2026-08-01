


from abc import abstractmethod
from typing import Any, Protocol, Sequence

from core.schemas.objects import UserStats
from database.dto import (
    SuggestionBaseDTO,
    SuggestionFullDTO,
    UserBotDTO,
    UserDTO,
    UserProfileDTO,
)


class UserRepositoryProtocol(Protocol):

    @abstractmethod
    async def get_by_id(self, user_id: int) -> UserDTO | None:
        ...

    @abstractmethod
    async def update(self, user_id: int, **data) -> None:
        ...

    @abstractmethod
    async def get_or_create(self, prep_user_dto: UserDTO) -> UserDTO:
        ...

    @abstractmethod
    async def create(self, dto: UserDTO) -> UserDTO:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


class UserProfileRepositoryProtocol(Protocol):

    @abstractmethod
    async def get(self, user_id: int) -> UserProfileDTO | None:
        ...

    @abstractmethod
    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        ...

    @abstractmethod
    async def create(self, user_id: int) -> UserProfileDTO:
        ...

    @abstractmethod
    async def update(self, user_id: int, **data) -> None:
        ...

    @abstractmethod
    async def get_active(self) -> Sequence[UserProfileDTO]:
        ...

    @abstractmethod
    async def get_admins(self) -> Sequence[UserProfileDTO]:
        ...

    @abstractmethod
    async def get_banned(self) -> Sequence[UserProfileDTO]:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...

    @abstractmethod
    async def admins_count(self) -> int:
        ...

    @abstractmethod
    async def banned_count(self) -> int:
        ...

    @abstractmethod
    async def bot_user_stats(self) -> Any:
        ...

    @abstractmethod
    async def decline_all_suggestions(self, user_id: int) -> None:
        ...


class SuggestionRepositoryProtocol(Protocol):

    @abstractmethod
    async def get_by_id(self, suggestion_id: int) -> SuggestionFullDTO | None:
        ...

    @abstractmethod
    async def update(self, suggestion_id: int, **data: Any):
        ...

    @abstractmethod
    async def save(self, dto: SuggestionBaseDTO):
        ...

    @abstractmethod
    async def create(
        self,
        author_id: int,
        anonymous: bool,
        mediainfo: list[Any],
        caption: str | None,
        media_group_id: str | None,
        forwarded_from: str | None,
    ):
        ...

    @abstractmethod
    async def get_active(self, limit=10, offset=0) -> Sequence[SuggestionFullDTO]:
        ...

    @abstractmethod
    async def user_stats(self, user_id: int) -> UserStats | None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


class MediaRepositoryProtocol(Protocol):

    @abstractmethod
    async def count(self) -> int:
        ...

class UserBotRepositoryProtocol(Protocol):

    @abstractmethod
    async def get(self, bot_id: int) -> UserBotDTO | None:
        ...

    @abstractmethod
    async def get_active(self) -> Sequence[UserBotDTO]:
        ...

    @abstractmethod
    async def get_by_owner_id(self, owner_id: int) -> Sequence[UserBotDTO]:
        ...

    @abstractmethod
    async def create(
        self,
        token: str,
        bot_id: int,
        username: str,
        owner_id: int,
        channel_id: int,
        channel_name: str,
    ) -> None:
        ...

    async def update(self, bot_id: int, **data: Any): ...

    async def save(self, dto: UserBotDTO): ...
