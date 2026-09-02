from typing import Any, Protocol

from aiogram.types import InlineKeyboardMarkup, MediaUnion, Message, MessageId

from database.dto import SuggestionFullDTO, UserDTO, UserProfileDTO

SendTarget = UserDTO | UserProfileDTO | int


class MessageNotifierProtocol(Protocol):
    async def send_text(
        self,
        target: SendTarget,
        i18n_key: str,
        i18n_kwargs: dict | None = None,
        kb: Any | None = None,
    ) -> Message: ...

    async def send_mediagroup(
        self,
        target: SendTarget,
        media: list[MediaUnion],
    ) -> list[Message]: ...

    async def forward(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]: ...

    async def copy(
        self,
        target: SendTarget,
        source_chat: int,
        message_ids: list[int],
    ) -> list[MessageId]: ...

    async def edit(
        self,
        chat_id: int,
        message_id: int,
        new_text: str,
        new_kb: InlineKeyboardMarkup | None = None,
    ) -> bool | Message: ...


class SuggestionNotifierProtocol(Protocol):
    async def send_to_admin(self, admin: SendTarget, dto: SuggestionFullDTO): ...
    async def send_to_channel(self, channel_id: int, dto: SuggestionFullDTO): ...
