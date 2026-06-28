

from types import TracebackType
from typing import Protocol, Self, Type
from abc import abstractmethod

from interfaces import (
    UserRepositoryProtocol,
    SuggestionRepositoryProtocol,
    MediaRepositoryProtocol,
)

class UnitOfWorkProtocol(Protocol):
    
    users: UserRepositoryProtocol
    suggestions: SuggestionRepositoryProtocol
    medias: MediaRepositoryProtocol

    @abstractmethod
    async def transaction(self): ...

    @abstractmethod
    async def commit(self): ...

    @abstractmethod
    async def rollback(self): ...