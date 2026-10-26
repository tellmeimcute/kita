from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import ChatFullInfo, ChatMemberAdministrator
from aiogram.types import User as AiogramUser
from aiogram.utils.token import TokenValidationError, extract_bot_id
from loguru import logger

from core.exceptions import (
    BadRequestError,
    InsufficientPermissionsError,
    InvalidTokenError,
    NotAChannelError,
    TokenFromAnotherBotError,
    UserbotBanned,
    UserbotError,
    UserbotNotFoundError,
)
from database.dto import UserBotDTO, UserDTO


@dataclass(frozen=True)
class UserbotProbe:
    bot_info: AiogramUser | None = None
    channel: ChatFullInfo | None = None
    member: ChatMemberAdministrator | None = None
    error: UserbotError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


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


async def probe_token(tmp_bot_settings: dict, token: str) -> AiogramUser:
    """Check that the token is alive and return the bot info."""
    try:
        async with Bot(token=token, **tmp_bot_settings) as tmp_bot:
            return await tmp_bot.get_me()
    except TelegramUnauthorizedError:
        logger.info("Userbot token probe failed: invalid token")
        raise InvalidTokenError() from None


async def probe_userbot(bot: Bot, channel_id: int | str) -> UserbotProbe:
    """Single Telegram probe: bot is alive, channel exists, can post messages."""
    bot_info = None
    try:
        bot_info = await bot.get_me()
        channel = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(channel.id, bot.id)
    except TelegramUnauthorizedError:
        logger.info("Userbot probe failed: invalid token")
        return UserbotProbe(bot_info=bot_info, error=InvalidTokenError())
    except TelegramBadRequest as e:
        logger.info("Userbot probe failed: {}", e.message)
        return UserbotProbe(bot_info=bot_info, error=BadRequestError())

    if channel.type != "channel":
        logger.info("Userbot probe failed: provided channel_id is not a channel")
        return UserbotProbe(bot_info=bot_info, channel=channel, error=NotAChannelError())

    is_admin = member.status == ChatMemberStatus.ADMINISTRATOR
    if not is_admin or not member.can_post_messages:
        logger.info("Userbot probe failed: not enough post message permission")
        return UserbotProbe(
            bot_info=bot_info,
            channel=channel,
            member=member,
            error=InsufficientPermissionsError(),
        )

    return UserbotProbe(bot_info=bot_info, channel=channel, member=member)


def userbot_action_auth(user_dto: UserDTO, userbot: UserBotDTO | None) -> None:
    if not userbot or userbot.owner_id != user_dto.user_id:
        raise UserbotNotFoundError()
    if userbot.banned:
        raise UserbotBanned()
