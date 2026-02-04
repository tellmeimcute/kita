from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


import asyncio
from time import time
from typing import Any, Awaitable, Callable, Dict, List, Union


class MediaGroutMiddleware(BaseMiddleware):
    """
    Помещает в album все обьекты media group
    Дополнительно шлет media_group_id
    """

    def __init__(self, latency: float = 0.1) -> None:
        self.latency = latency
        self.albums: Dict[str, Dict[str, Any]] = {}  # TODO: Переместить в редис

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        group_id = event.media_group_id
        if group_id not in self.albums:
            self.albums[group_id] = {"messages": [], "last": time(), "task": None}

        album = self.albums[group_id]
        album["messages"].append(event)
        album["last"] = time()

        if album["task"]:
            album["task"].cancel()

        async def wait_and_handle():
            await asyncio.sleep(self.latency)

            if time() - album["last"] < self.latency:
                return

            messages: List[Message] = album["messages"]
            messages.sort(key=lambda m: m.message_id)

            del self.albums[group_id]

            data["album"] = messages
            data["media_group_id"] = group_id

            try:
                await handler(event, data)
            except Exception as e:
                print(e)

        task = asyncio.create_task(wait_and_handle())
        album["task"] = task

        return None
