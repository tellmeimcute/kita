from typing import Final

from aiogram.methods import (
    CopyMessage,
    CopyMessages,
    EditMessageCaption,
    EditMessageMedia,
    EditMessageReplyMarkup,
    EditMessageText,
    ForwardMessage,
    ForwardMessages,
    SendAnimation,
    SendAudio,
    SendContact,
    SendDice,
    SendDocument,
    SendGame,
    SendInvoice,
    SendLocation,
    SendMediaGroup,
    SendMessage,
    SendPaidMedia,
    SendPhoto,
    SendPoll,
    SendSticker,
    SendVenue,
    SendVideo,
    SendVideoNote,
    SendVoice,
    TelegramMethod,
)
from redis.asyncio import Redis

from database.redis import KitaKeyBuilder, RedisKey

RESERVE_SCRIPT: Final = """
local bot_key        = KEYS[1]
local chat_key       = KEYS[2]
local bot_period     = tonumber(ARGV[1])
local bot_tolerance  = tonumber(ARGV[2])
local chat_period    = tonumber(ARGV[3])
local chat_tolerance = tonumber(ARGV[4])
local bot_cost       = tonumber(ARGV[5])
local chat_cost      = tonumber(ARGV[6])

local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

local function reserve(key, period, tolerance, cost)
  local tat = tonumber(redis.call('GET', key))
  if not tat or tat < now then tat = now end

  local allow_at = tat - tolerance
  local wait = 0
  if now < allow_at then wait = allow_at - now end

  local new_tat = tat + period * cost
  local ttl = math.ceil((new_tat - now + tolerance) * 1000) + 1000
  if ttl < 1 then ttl = 1 end

  redis.call('SET', key, tostring(new_tat), 'PX', ttl)

  return wait
end

local wait_bot = reserve(bot_key, bot_period, bot_tolerance, bot_cost)
local wait_chat = 0
if chat_key ~= '' and chat_cost > 0 then
  wait_chat = reserve(chat_key, chat_period, chat_tolerance, chat_cost)
end

return math.ceil(math.max(wait_bot, wait_chat) * 1000)
"""

SINGLE_MESSAGE_METHODS: Final = (
    SendMessage,
    SendPhoto,
    SendAudio,
    SendDocument,
    SendVideo,
    SendAnimation,
    SendVoice,
    SendVideoNote,
    SendPaidMedia,
    SendLocation,
    SendVenue,
    SendContact,
    SendPoll,
    SendDice,
    SendSticker,
    SendGame,
    SendInvoice,
    CopyMessage,
    CopyMessages,
    ForwardMessage,
    ForwardMessages,
    EditMessageText,
    EditMessageCaption,
    EditMessageMedia,
    EditMessageReplyMarkup,
)


def message_cost(method: TelegramMethod) -> int:
    """Cost in messages for the bot-wide budget; 0 means "not a message send"."""
    if isinstance(method, SendMediaGroup):
        return len(method.media)

    if isinstance(method, SINGLE_MESSAGE_METHODS):
        return 1

    return 0


def chat_id_of(method: TelegramMethod) -> int | str | None:
    return getattr(method, "chat_id", None)


class TgApiLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        rate: float,
        burst: int,
        chat_rate: float,
        chat_burst: int,
    ):
        self._period = 1 / rate
        self._tolerance = (burst - 1) * self._period
        self._chat_period = 1 / chat_rate
        self._chat_tolerance = (chat_burst - 1) * self._chat_period
        self._key_builder = KitaKeyBuilder(with_user_id=False)
        self._script = redis.register_script(RESERVE_SCRIPT)

    def _keys(self, bot_id: int, chat_id: int | str | None) -> tuple[str, str]:
        keybase = RedisKey(bot_id=bot_id)
        bot_key = self._key_builder.build(keybase, ["api", "gcra"])

        if not chat_id:
            return bot_key, ""

        chat_key = self._key_builder.build(keybase, ["api", "chat", str(chat_id), "gcra"])
        return bot_key, chat_key

    async def reserve(
        self,
        bot_id: int,
        *,
        cost: int,
        chat_id: int | str | None = None,
        chat_cost: int = 1,
    ) -> float:
        """Seconds to wait before this call may be sent; 0 means "now"."""
        bot_key, chat_key = self._keys(bot_id, chat_id)

        wait_ms = await self._script(
            keys=[bot_key, chat_key],
            args=[
                self._period,
                self._tolerance,
                self._chat_period,
                self._chat_tolerance,
                cost,
                chat_cost if chat_id else 0,
            ],
        )

        return wait_ms / 1000
