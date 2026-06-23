


from core.schemas.message_payload import MessagePayload
from .base import KitaException


class UnsupportedPayload(KitaException):
    def __init__(self, payload: MessagePayload | None = None):
        self.payload = payload