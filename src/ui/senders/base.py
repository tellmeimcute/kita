import asyncio
from abc import ABC, abstractmethod

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message, MessageId
from loguru import logger

MAX_RETRY = 3


class BaseSender(ABC):
    target_id: int

    @abstractmethod
    async def _send(self) -> Message | list[Message] | list[MessageId]: ...

    async def send(self):
        retries = 0
        while True:
            try:
                return await self._send()
            except TelegramRetryAfter as e:
                if retries + 1 > MAX_RETRY:
                    logger.error("Rate limited on {} to {}, giving up", self.name, self.target_id)
                    return None
                wait = max(float(e.retry_after), 1.0)
                logger.warning(
                    "Telegram Rate limited on {} to {}, retrying in {}",
                    self.name,
                    self.target_id,
                    wait,
                )
                await asyncio.sleep(wait)
                retries += 1
            except Exception as e:
                logger.exception(
                    "Failed to execute strategy {} to target {}: {}", self.name, self.target_id, e
                )
                return None

    @property
    def name(self):
        return self.__class__.__qualname__
