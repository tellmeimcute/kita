from core.exceptions import UserbotError
from database.dto import UserBotDTO, UserDTO
from utils.userbot_probe import probe_userbot

from .base_toggle import BaseToggle


class UserbotActivateUseCase(BaseToggle):
    __slots__ = ()

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> UserBotDTO:
        userbot = await super().execute(caller_dto, userbot_id)

        if userbot.active:
            return userbot

        bot = self._bot_for(userbot)

        try:
            await probe_userbot(bot, userbot.channel_id)
        except UserbotError:
            await self.deactivate(bot, userbot)
            raise

        return await self.activate(bot, userbot)
