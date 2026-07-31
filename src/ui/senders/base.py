
from abc import ABC, abstractmethod
from logging import getLogger

from aiogram.types import Message, MessageId

logger = getLogger("kita.senders")

class BaseSender(ABC):
    target_id: int

    @abstractmethod
    async def _send(self) -> Message | list[Message] | list[MessageId]:
        ...

    async def send(self):
        try:
            return await self._send()
        except Exception as e:
            logger.error(
                "Failed to execute strategy %s to target %s: %s",
                self.name, self.target_id, e,
            )

    @property
    def name(self):
        return self.__class__.__qualname__
    