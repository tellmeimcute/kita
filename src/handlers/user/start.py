from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Config
from database.dto import UserDTO
from handlers.keyboards import get_main_kb_by_role
from helpers.message_payload import MessagePayload
from services.notifier import Notifier

from aiogram.utils.i18n import lazy_gettext as __

router = Router(name="start_handlers")


@router.message(CommandStart())
async def start(
    message: Message,
    user_dto: UserDTO,
    config: Config,
    notifier: Notifier,
):
    main_kb = get_main_kb_by_role(user_dto.role)
    i18n_kwargs = {"channel_name": html.bold(config.channel_name)}

    payload = MessagePayload(i18n_key="start_msg", i18n_kwargs=i18n_kwargs, reply_markup=main_kb)
    await notifier.notify_user(user_dto, payload)


@router.message(F.text == __("cancel_command"))
@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: Notifier,
):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    kb = get_main_kb_by_role(user_dto.role)
    payload = MessagePayload(i18n_key="state_reset", reply_markup=kb)
    await notifier.notify_user(user_dto, payload=payload)
