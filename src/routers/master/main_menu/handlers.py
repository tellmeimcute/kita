from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode

from ui.state_groups import RegistrarMenuSG

router = Router(name="registrar")


@router.message(CommandStart())
async def master_start_menu(message: Message, state: FSMContext, dialog_manager: DialogManager):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    await dialog_manager.start(
        RegistrarMenuSG.menu,
        show_mode=ShowMode.DELETE_AND_SEND,
    )
