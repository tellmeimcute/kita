from .base import KitaException


class UserbotError(KitaException):
    error_key: str


class InvalidTokenError(UserbotError):
    error_key = "reg_bot_token_invalid"


class ChannelNotFoundError(UserbotError):
    error_key = "reg_bot_channel_id_error"


class NotAChannelError(UserbotError):
    error_key = "reg_bot_not_a_channel_error"


class InsufficientPermissionsError(UserbotError):
    error_key = "reg_bot_permission_error"


class TokenFromAnotherBotError(UserbotError):
    error_key = "reg_bot_token_from_another_bot"


class UserbotAlreadyExistsError(UserbotError):
    error_key = "reg_bot_alredy_exist"


class BadRequestError(UserbotError):
    error_key = "reg_bot_bad_request"


class UserbotNotFoundError(UserbotError):
    error_key = "userbot_not_found"


class UserbotBanned(UserbotError):
    error_key = "userbot_is_banned"
