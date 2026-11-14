from database.dto import UserBotDTO, UserDTO

from .base_toggle import BaseToggle


class UserbotDeactivateUseCase(BaseToggle):
    __slots__ = ()

    async def execute(self, caller_dto: UserDTO, userbot_id: int) -> UserBotDTO:
        userbot = await super().execute(caller_dto, userbot_id)

        if not userbot.active:
            return userbot

        bot = self._bot_for(userbot)
        return await self.deactivate(bot, userbot)
