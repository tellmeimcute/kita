
from aiogram import Bot
from .base import BaseSender

class MessageTransfer(BaseSender):
    def __init__(
        self,
        bot: Bot,
        target_id: int,
        from_chat_id: int,
        message_ids: list[int],
    ):
        self.bot = bot
        self.target_id = target_id

        self.from_chat_id = from_chat_id
        self.message_ids = message_ids

class CopyTransfer(MessageTransfer):
    async def send(self):
        return await self.bot.copy_messages(
            chat_id=self.target_id,
            from_chat_id=self.from_chat_id,
            message_ids=self.message_ids,
        )
    
class ForwardTransfer(MessageTransfer):
    async def send(self):
        return await self.bot.forward_messages(
            chat_id=self.target_id,
            from_chat_id=self.from_chat_id,
            message_ids=self.message_ids,
        )