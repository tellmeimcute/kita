
from abc import ABC, abstractmethod

class BaseSender(ABC):
    @abstractmethod
    async def send(self):
        ...

    @property
    def name(self):
        return self.__class__.__qualname__