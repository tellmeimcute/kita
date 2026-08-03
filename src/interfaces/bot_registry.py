import contextvars
from abc import abstractmethod
from typing import Protocol

from aiogram import Bot


class BotRegistryProtocol(Protocol):
    @property
    def bot_settings(self) -> dict: ...

    @property
    def allowed_updates(self) -> list[str]: ...

    @allowed_updates.setter
    def allowed_updates(self, value): ...

    @abstractmethod
    def register(self, bot: Bot) -> None: ...

    @abstractmethod
    def get(self, bot_id: int) -> Bot: ...

    @abstractmethod
    def get_or_create(self, bot_id: int, token: str) -> Bot: ...

    @abstractmethod
    def remove(self, bot_id: int): ...

    @abstractmethod
    def get_all(self) -> list[Bot]: ...

    @abstractmethod
    def get_current(self) -> Bot | None: ...

    @abstractmethod
    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]: ...

    @abstractmethod
    def reset_current(self, token: contextvars.Token[Bot | None]) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
