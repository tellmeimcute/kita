from typing import Protocol

from .repository import (
    MediaRepositoryProtocol,
    SuggestionRepositoryProtocol,
    UserProfileRepositoryProtocol,
    UserRepositoryProtocol,
)


class UnitOfWorkProtocol(Protocol):
    users: UserRepositoryProtocol
    profiles: UserProfileRepositoryProtocol
    suggestions: SuggestionRepositoryProtocol
    medias: MediaRepositoryProtocol

    async def transaction(self): ...

    async def commit(self): ...

    async def rollback(self): ...
