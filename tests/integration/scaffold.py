from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatFullInfo
from aiogram.types import User as AiogramUser

from interfaces import BotContextProtocol, BotResolverProtocol
from services.bots import BotCache

BOT_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
BOT_ID = 123456789
BOT_USERNAME = "test_userbot"
USERBOT_ALLOWED_UPDATES = ("callback_query", "message", "my_chat_member")

CHANNEL_ID = -100123456789
CHANNEL_NAME = "Test Channel"
CHANNEL_INPUT = "123456789"


def make_tg_channel() -> MagicMock:
    channel = MagicMock(spec=ChatFullInfo)
    channel.id = CHANNEL_ID
    channel.full_name = CHANNEL_NAME
    channel.type = "channel"
    return channel


def make_tg_bot(channel: MagicMock, token: str = BOT_TOKEN) -> MagicMock:
    bot = MagicMock(spec=Bot)
    bot.id = BOT_ID
    bot.token = token
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


class FakeBotSessions:
    """The Telegram seam: hands out one prepared bot for any token."""

    def __init__(self) -> None:
        self.temp_bot = MagicMock(side_effect=self._temp_bot)
        self.reset()

    def reset(self) -> None:
        self.channel: MagicMock = make_tg_channel()
        self.bot: MagicMock = make_tg_bot(self.channel)
        self.temp_bot.reset_mock()

    def create(self, token: str) -> Bot:
        self.bot.token = token
        return self.bot

    async def close(self) -> None:
        pass

    @asynccontextmanager
    async def _temp_bot(self, token: str) -> AsyncGenerator[Bot]:
        self.bot.token = token
        yield self.bot


@dataclass
class BotStack:
    """The bot stack as tests see it: one fake seam over the real collaborators."""

    sessions: FakeBotSessions
    cache: BotCache
    context: BotContextProtocol
    resolver: BotResolverProtocol

    @property
    def bot(self) -> MagicMock:
        return self.sessions.bot

    @property
    def channel(self) -> MagicMock:
        return self.sessions.channel

    def reset(self) -> None:
        self.sessions.reset()

        for bot in self.cache.all():
            self.cache.remove(bot.id)
        self.cache.put(self.sessions.bot)


class FakeWebhookService:
    def __init__(self) -> None:
        self.set_webhook = AsyncMock()
        self.remove_webhook = AsyncMock()

    def reset(self) -> None:
        self.set_webhook.reset_mock()
        self.remove_webhook.reset_mock()
