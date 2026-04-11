
import logging
from typing import ClassVar
from abc import ABC

from aiogram import BaseMiddleware, Router

logger = logging.getLogger("kita.middleware")

class KitaMiddleware(BaseMiddleware, ABC):
    __event__types__: ClassVar[set[str]] = {"message", "callback_query"}

    def setup(self, router: Router):
        for event_name, observer in router.observers.items():
            if event_name in self.__event__types__:
                observer.outer_middleware(self)
                logger.debug(
                    "%s registered to event %s on router: %s",
                    self.__class__.__qualname__, event_name, router.name
                )
        return self
