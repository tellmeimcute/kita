
import asyncio
from itertools import batched

from aiogram.types import Message, MessageOriginChannel

from core.i18n_translator import Translator
from core.schemas.data import MassMessageData
from services import NotifierService, UserService


class BroadcastUseCase:

    __slots__ = (
        "_user_service",
        "_notifier",
        "_translator",
    )

    def __init__(
        self,
        user_service: UserService,
        notifier: NotifierService,
        translator: Translator,
    ):
        self._user_service = user_service
        self._notifier = notifier
        self._translator = translator

    async def prepare(self, message: Message, album: tuple[Message, ...]) -> MassMessageData:
        active = await self._user_service.get_active()

        is_forwarded = isinstance(message.forward_origin, MessageOriginChannel)
        return MassMessageData(
            users=active,
            is_forwarded=is_forwarded,
            source_chat_id=message.chat.id,
            source_message_ids=[m.message_id for m in album],
        )

    def estimate_time(self, data: MassMessageData) -> float:
        return (data.users_count / self._notifier.chunk_size) * self._notifier.chunk_delay

    async def execute(
        self,
        data: MassMessageData,
        status_message: Message,
    ):
        send_func = (
            self._notifier.forward_messages
            if data.is_forwarded
            else self._notifier.copy_messages
        )

        for chunk in batched(data.users, self._notifier.chunk_size, strict=False):
            tasks = [
                send_func(user_dto, data.source_message_ids, data.source_chat_id)
                for user_dto in chunk
            ]
            result = await asyncio.gather(*tasks)

            success = [r for r in result if r]
            data = data.model_copy(
                update={
                    "progress": data.progress + len(result),
                    "success": data.success + len(success),
                    "failure": data.failure + len(result) - len(success),
                }
            )

            if data.progress % 10 == 0 or data.progress == data.users_count:
                i18n_kwargs = data.model_dump()
                i18n_kwargs["status"] = self._translator.translate(
                    i18n_key="completed" if data.status else "in_process"
                )
                new_status = self._translator.i18n_text("broadcast_status_text", i18n_kwargs)
                await self._notifier.edit_message_text(status_message, new_status)

            await asyncio.sleep(self._notifier.chunk_delay)
