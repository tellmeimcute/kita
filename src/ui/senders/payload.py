
from aiogram import Bot
from aiogram.types import Message
from helpers.schemas.message_payload import MessagePayload
from core.i18n_translator import Translator
from .base import BaseSender


class MessageSender(BaseSender):
    def __init__(
        self,
        bot: Bot,
        target_id: int,
        payload: MessagePayload,
        silent: bool = True,
        translator: Translator | None = None
    ):
        self.bot = bot
        self.target_id = target_id
        self.silent = silent
        self.payload = payload

        self.translator = translator

class MediaGroupSender(MessageSender):
    async def send(self) -> list[Message]:
        return await self.bot.send_media_group(self.target_id, self.payload.content, disable_notification=self.silent)

class TextSender(MessageSender):
    async def send(self) -> Message:
        if not self.translator:
            raise ValueError("Translator is required for TextSender")
        
        content = self.translator.get_i18n_text(self.payload.i18n_key, self.payload.i18n_kwargs)
        return await self.bot.send_message(
            chat_id=self.target_id,
            text=content,
            reply_markup=self.payload.reply_markup,
            disable_notification=self.silent,
        )