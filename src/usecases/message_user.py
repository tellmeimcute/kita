from aiogram.utils.i18n import I18n

from database.dto import UserDTO
from interfaces import MessageNotifierProtocol


class MessageUserUseCase:
    def __init__(self, notifier: MessageNotifierProtocol, i18n: I18n):
        self.notifier = notifier
        self.i18n = i18n

    async def execute(
        self,
        target: UserDTO,
        caller: UserDTO,
        album_ids: list[int],
        source: int,
    ):
        sended_msg = await self.notifier.copy(target, source, album_ids)
        with self.i18n.context():
            with self.i18n.use_locale(target.language_code):
                await self.notifier.send_text(target, "notify_you_receive_message")

            with self.i18n.use_locale(caller.language_code):
                i18n_key = "message_delivered" if sended_msg else "message_not_delivered"
                await self.notifier.send_text(caller, i18n_key)
