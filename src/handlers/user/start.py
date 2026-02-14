from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Config
from helpers.message_payload import MessagePayload
from database.models import UserAlchemy
from services.notifier import Notifier

from handlers.keyboards import (
    get_main_kb_by_role,
)


router = Router(name="start_handlers")


@router.message(CommandStart())
async def start(
    message: Message,
    user_alchemy: UserAlchemy,
    config: Config,
    notifier: Notifier,
):
    main_kb = get_main_kb_by_role(user_alchemy.role)
    i18n_kwargs = {"channel_name": html.bold(config.channel_name)}

    payload = MessagePayload(i18n_key="start_msg", i18n_kwargs=i18n_kwargs, reply_markup=main_kb)
    await notifier.notify_user(user_alchemy, payload)


@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    notifier: Notifier,
):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    kb = get_main_kb_by_role(user_alchemy.role)

    payload = MessagePayload(i18n_key="state_reset", reply_markup=kb)
    await notifier.notify_user(user_alchemy, payload=payload)


@router.message(F.text.lower() == "отмена")
async def cancel_state(
    message: Message,
    state: FSMContext,
    user_alchemy: UserAlchemy,
    notifier: Notifier,
):
    await cmd_cancel_state(message, state, user_alchemy, notifier)
