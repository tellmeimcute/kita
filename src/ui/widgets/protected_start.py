


from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Start

from database.dto import UserDTO

class ProtectedStart(Start):
    async def _on_click(
        self,
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
    ):
        user_dto: UserDTO = manager.middleware_data.get("user_dto")

        if not user_dto.is_admin:
            return await callback.answer("Not enough permission!")

        if self.user_on_click:
            await self.user_on_click(callback, self, manager)
        await manager.start(
            state=self.state,
            data=self.start_data,
            mode=self.mode,
            show_mode=self.show_mode,
        )
