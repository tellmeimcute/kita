from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.types import ChatFullInfo, ChatMemberAdministrator, User
from aiogram.utils.token import TokenValidationError, extract_bot_id
from loguru import logger


@dataclass(frozen=True)
class UserBotCheckResult:
    success: bool
    detail_i18n_key: str | None = None

    bot_info: User | None = None
    channel: ChatFullInfo | None = None
    channel_admin: ChatMemberAdministrator | None = None
    token: str | None = None
    bot_id: int | None = None


class UserBotChecker:
    def get_channel_id(self, input_str: str):
        provided = input_str.strip()
        return provided if provided.startswith("@") else int("-100" + provided)

    async def check_token(
        self, target_bot_id: int | None, token: str, bot_settings: dict
    ) -> UserBotCheckResult:
        try:
            token = token.strip()
            token_bot_id = extract_bot_id(token)
        except (TokenValidationError, AttributeError):
            detail_i18n_key = "reg_bot_token_invalid"
            return UserBotCheckResult(success=False, detail_i18n_key=detail_i18n_key)

        if target_bot_id and target_bot_id != token_bot_id:
            detail_i18n_key = "reg_bot_token_from_another_bot"
            return UserBotCheckResult(success=False, detail_i18n_key=detail_i18n_key)

        try:
            async with Bot(token=token, **bot_settings) as tmp_bot:
                bot_info = await tmp_bot.get_me()
        except TelegramUnauthorizedError:
            logger.info("Userbot check failed: invalid token")
            detail_i18n_key = "reg_bot_token_invalid"
            return UserBotCheckResult(success=False, detail_i18n_key=detail_i18n_key)

        return UserBotCheckResult(
            success=True,
            bot_info=bot_info,
            token=token,
            bot_id=token_bot_id,
        )

    async def check_channel_rights(self, bot: Bot, channel_id: int | str):
        try:
            channel_member = await bot.get_chat_member(channel_id, bot.id)
        except TelegramBadRequest:
            return None

        is_admin = channel_member.status == ChatMemberStatus.ADMINISTRATOR
        if not is_admin or not channel_member.can_post_messages:
            return None
        return channel_member

    async def full_check(self, bot: Bot, channel_id: int | str) -> UserBotCheckResult:
        status = None

        try:
            bot_info = await bot.get_me()
            channel = await bot.get_chat(channel_id)
            channel_admin = await self.check_channel_rights(bot, channel.id)
        except TelegramUnauthorizedError:
            logger.info("Userbot check failed: invalid token")
            detail_i18n_key = "reg_bot_token_invalid"
            status = UserBotCheckResult(success=False, detail_i18n_key=detail_i18n_key)
        except TelegramBadRequest as e:
            logger.exception("Userbot check failed: {}", e.message)
            detail_i18n_key = "reg_bot_bad_request"
            status = UserBotCheckResult(
                success=False, detail_i18n_key=detail_i18n_key, bot_info=bot_info
            )

        if status:
            return status

        if not channel_admin:
            return UserBotCheckResult(
                success=False,
                detail_i18n_key="reg_bot_permission_error",
                bot_info=bot_info,
                channel=channel,
                channel_admin=channel_admin,
            )

        return UserBotCheckResult(
            success=True,
            detail_i18n_key="reg_bot_check_success",
            bot_info=bot_info,
            channel=channel,
            channel_admin=channel_admin,
        )
