from .bot import BotNotRegisteredError
from .payload import UnsupportedPayload
from .sql import UserImmuneError
from .userbot import (
    BadRequestError,
    ChannelNotFoundError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    TokenFromAnotherBotError,
    UserbotAlreadyExistsError,
    UserbotBanned,
    UserbotError,
    UserbotNotFoundError,
)

__all__ = (
    "BotNotRegisteredError",
    "UnsupportedPayload",
    "UserImmuneError",
    "UserbotError",
    "InvalidTokenError",
    "ChannelNotFoundError",
    "NotAChannelError",
    "InsufficientPermissionsError",
    "UserbotAlreadyExistsError",
    "BadRequestError",
    "UserbotNotFoundError",
    "UserbotBanned",
    "TokenFromAnotherBotError",
)
