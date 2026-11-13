from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import ChatFullInfo
from aiogram.types import User as AiogramUser
from aiogram.utils.token import TokenValidationError, extract_bot_id
from loguru import logger

from core.exceptions import (
    BadRequestError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    TokenFromAnotherBotError,
)


@dataclass(frozen=True)
class UserbotProbe:
    bot_info: AiogramUser
    channel: ChatFullInfo


def validate_channel_id(input_str: str | None):
    if not input_str:
        return None

    provided = input_str.strip()

    if provided.startswith("@"):
        channel_id = provided
    elif provided.startswith("-100") and provided[4:].isdigit():
        channel_id = int(provided)
    elif provided.isdigit():
        channel_id = int("-100" + provided)
    else:
        return None

    return channel_id


def parse_token(raw_token: str | None, expected_bot_id: int | None = None) -> str:
    """Validate the token format and return its normalized form.

    Raises ``InvalidTokenError``/``TokenFromAnotherBotError``.
    """
    try:
        token = raw_token.strip()
        token_bot_id = extract_bot_id(token)
    except (TokenValidationError, AttributeError):
        raise InvalidTokenError() from None

    if expected_bot_id and expected_bot_id != token_bot_id:
        raise TokenFromAnotherBotError()

    return token


async def probe_token(bot: Bot) -> AiogramUser:
    """Check that the token is alive and return the bot info."""
    try:
        return await bot.get_me()
    except TelegramUnauthorizedError:
        logger.info("Userbot token probe failed: invalid token")
        raise InvalidTokenError() from None


async def probe_userbot(bot: Bot, channel_id: int | str) -> UserbotProbe:
    """Bot is alive, the chat is a channel and the bot may post there.

    Raises ``UserbotError`` on the first failed check.
    """
    bot_info = await probe_token(bot)

    try:
        channel = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(channel.id, bot.id)
    except TelegramBadRequest as e:
        logger.info("Userbot probe failed: {}", e.message)
        raise BadRequestError() from None

    if channel.type != "channel":
        logger.info("Userbot probe failed: provided channel_id is not a channel")
        raise NotAChannelError()

    if member.status != ChatMemberStatus.ADMINISTRATOR or not member.can_post_messages:
        logger.info("Userbot probe failed: not enough post message permission")
        raise InsufficientPermissionsError()

    return UserbotProbe(bot_info=bot_info, channel=channel)
