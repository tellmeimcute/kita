

from abc import abstractmethod
from typing import Protocol, Sequence, Any

from core.schemas.objects import UserStats
from database.dto import UserDTO, SuggestionBaseDTO, SuggestionFullDTO
from services.message_parser import MediaInfo

class UserRepositoryProtocol(Protocol):

    @abstractmethod
    async def get_by_id(self, user_id: int) -> UserDTO | None:
        ...

    @abstractmethod
    async def update(self, user_id: int, **data) -> None:
        ...

    @abstractmethod
    async def save(self, dto: UserDTO) -> UserDTO:
        ...

    @abstractmethod
    async def create(self, dto: UserDTO) -> UserDTO:
        ...
    
    @abstractmethod
    async def get_active(self) -> Sequence[UserDTO]:
        ...
    
    @abstractmethod
    async def get_admins(self) -> Sequence[UserDTO]:
        ...

    @abstractmethod
    async def get_banned(self) -> Sequence[UserDTO]:
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
    async def user_stats(self) -> Any:
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
        mediainfo: list[MediaInfo],
        caption: str | None,
        media_group_id: str | None,
        forwarded_from: str | None,
    ):
        ...

    @abstractmethod
    async def get_active(self, limit=10, offset=0) -> Sequence[SuggestionFullDTO]:
        ...

    @abstractmethod
    async def get_user_stats(self, user_id: int) -> UserStats | None:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...
    

class MediaRepositoryProtocol(Protocol):
    
    @abstractmethod
    async def count(self) -> int:
        ...