from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiogram_dialog import DialogManager, StartMode

from database.dto import SuggestionFullDTO, UserDTO
from interfaces import (
    BotRegistryProtocol,
    MessageNotifierProtocol,
    SuggestionNotifierProtocol,
    SuggestionQueueProtocol,
)
from ui.state_groups import UserMenuSG
from utils.suggestion_utils import SuggestionUtils

from .base import BaseService


class SuggestionViewer(BaseService):
    __slots__ = (
        "suggestion_queue",
        "suggestion_notifier",
        "msg_notifier",
        "utils",
        "fsm",
    )

    def __init__(
        self,
        bot_registry: BotRegistryProtocol,
        suggestion_queue: SuggestionQueueProtocol,
        suggestion_notifier: SuggestionNotifierProtocol,
        suggestion_utils: SuggestionUtils,
        notifier: MessageNotifierProtocol,
        fsm_context: FSMContext,
    ):
        super().__init__(bot_registry)
        self.suggestion_queue = suggestion_queue
        self.suggestion_notifier = suggestion_notifier
        self.utils = suggestion_utils
        self.msg_notifier = notifier
        self.fsm = fsm_context

    async def advance(self, user_dto: UserDTO) -> bool:
        dto = await self.suggestion_queue.next_suggestion()
        if not dto:
            return False

        await self.suggestion_notifier.send_to_admin(user_dto, dto)

        data = {
            "current_suggestion": dto.model_dump(mode="json"),
        }

        await self.fsm.update_data(data)

        return True

    async def get_current(self) -> SuggestionFullDTO | None:
        data = await self.fsm.get_data()
        if raw := data.get("current_suggestion"):
            return SuggestionFullDTO.model_validate(raw)
        return None

    async def return_to_menu(self, manager: DialogManager, user_dto: UserDTO):
        await self.fsm.clear()
        await self.msg_notifier.send_text(
            user_dto, "suggestion_no_active", kb=ReplyKeyboardRemove()
        )
        return await manager.start(
            UserMenuSG.main,
            mode=StartMode.RESET_STACK,
        )
