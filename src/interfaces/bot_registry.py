
import contextvars
from abc import abstractmethod
from typing import Protocol

from aiogram import Bot


class BotRegistryProtocol(Protocol):

    @abstractmethod
    def register(self, bot: Bot) -> None: ...

    @abstractmethod
    def get(self, bot_id: int) -> Bot: ...

    @abstractmethod
    def get_current(self) -> Bot | None: ...

    @abstractmethod
    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]: ...

    @abstractmethod
    def reset_current(self, token: contextvars.Token[Bot | None]) -> None: ...
