import contextvars
from contextlib import AbstractAsyncContextManager
from typing import Protocol, overload

from aiogram import Bot


class BotContextProtocol(Protocol):
    """The bot this task handles: read it and scope an operation to it."""

    def get_current(self) -> Bot | None: ...

    def set_current(self, bot: Bot) -> contextvars.Token[Bot | None]: ...

    def reset_current(self, token: contextvars.Token[Bot | None]) -> None: ...

    def using(self, bot: Bot) -> AbstractAsyncContextManager[Bot]: ...


class BotResolverProtocol(Protocol):
    """Bots by id: a cached one, a throwaway one, or a forgotten one."""

    def get_or_create(self, bot_id: int, token: str) -> Bot: ...

    def remove(self, bot_id: int) -> None: ...

    def temp_bot(self, token: str) -> AbstractAsyncContextManager[Bot]: ...

    @overload
    def with_bot(
        self, bot_id: int, /, *, token: str | None = None
    ) -> AbstractAsyncContextManager[Bot]: ...

    @overload
    def with_bot(self, bot: Bot, /) -> AbstractAsyncContextManager[Bot]: ...


class BotSessionProtocol(Protocol):
    """Owns the aiohttp session every bot shares."""

    def create(self, token: str) -> Bot: ...

    def temp_bot(self, token: str) -> AbstractAsyncContextManager[Bot]: ...

    async def close(self) -> None: ...
