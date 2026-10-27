"""Общие данные и тест-дублёры для интеграционных тестов юзерботов."""

import contextvars
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatFullInfo
from aiogram.types import User as AiogramUser

BOT_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
BOT_ID = 123456789
BOT_USERNAME = "test_userbot"

CHANNEL_ID = -100123456789
CHANNEL_NAME = "Test Channel"
CHANNEL_INPUT = "123456789"


def make_tg_channel() -> MagicMock:
    channel = MagicMock(spec=ChatFullInfo)
    channel.id = CHANNEL_ID
    channel.full_name = CHANNEL_NAME
    channel.type = "channel"
    return channel


def make_tg_bot(channel: MagicMock) -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.id = BOT_ID
    bot.token = BOT_TOKEN
    bot.__aenter__ = AsyncMock(return_value=bot)
    bot.__aexit__ = AsyncMock(return_value=False)

    bot.get_me = AsyncMock(
        return_value=AiogramUser(id=BOT_ID, is_bot=True, first_name="Test", username=BOT_USERNAME)
    )
    bot.get_chat = AsyncMock(return_value=channel)
    bot.get_chat_member = AsyncMock(
        return_value=MagicMock(status=ChatMemberStatus.ADMINISTRATOR, can_post_messages=True)
    )

    return bot


class FakeBotRegistry:
    def __init__(self) -> None:
        self.allowed_updates: list[str] = []
        self._current: contextvars.ContextVar[Bot | None] = contextvars.ContextVar(
            "fake_current_bot", default=None
        )

        self.channel: MagicMock = make_tg_channel()
        self.bot: MagicMock = make_tg_bot(self.channel)

        self.register = MagicMock()
        self.get = MagicMock()
        self.get_or_create = MagicMock()
        self.remove = MagicMock()
        self.get_all = MagicMock()
        self.get_current = MagicMock(side_effect=self._get_current)
        self.set_current = MagicMock(side_effect=self._current.set)
        self.reset_current = MagicMock(side_effect=self._current.reset)
        self.close = AsyncMock()

        self.reset()

    def _get_current(self) -> Bot | None:
        return self._current.get() or self.bot

    def reset(self) -> None:
        self.channel = make_tg_channel()
        self.bot = make_tg_bot(self.channel)
        self._current.set(None)

        self.get.return_value = self.bot
        self.get_or_create.return_value = self.bot
        self.get_all.return_value = [self.bot]

        for method in (
            self.register,
            self.get,
            self.get_or_create,
            self.remove,
            self.get_all,
            self.get_current,
            self.set_current,
            self.reset_current,
            self.close,
        ):
            method.reset_mock()

    @asynccontextmanager
    async def temp_bot(self, token: str) -> AsyncGenerator[Bot]:
        yield self.bot

    @asynccontextmanager
    async def with_bot(
        self, bot_or_id: Bot | int, token: str | None = None
    ) -> AsyncGenerator[Bot]:
        bot = bot_or_id if isinstance(bot_or_id, Bot) else self.bot

        prev = self._current.set(bot)
        try:
            yield bot
        finally:
            self._current.reset(prev)


class FakeWebhookService:
    def __init__(self) -> None:
        self.set_webhook = AsyncMock()
        self.remove_webhook = AsyncMock()

    def reset(self) -> None:
        self.set_webhook.reset_mock()
        self.remove_webhook.reset_mock()
