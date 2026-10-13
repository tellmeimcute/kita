from typing import Protocol


class SuggestionTaskDispatcherProtocol(Protocol):
    async def accepted(self, bot_id: int, suggestion_id: int) -> None: ...
