


from helpers.schemas.message_payload import MessagePayload
from .i18n_base import KitaException


class UnsupportedPayload(KitaException):
    def __init__(
        self,
        payload: MessagePayload | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.payload = payload