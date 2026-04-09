from aiogram import Router, html
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from dishka import FromDishka
from config import RuntimeConfig
from database.dto import UserDTO
from routers.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter
from helpers.schemas.message_payload import MessagePayload
from services.notifier import NotifierService

router = Router(name="start_handlers")


@router.message(CommandStart())
async def start(
    message: Message,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    runtime_config: FromDishka[RuntimeConfig],
):
    i18n_kwargs = {"channel_name": html.bold(runtime_config.channel_name)}

    payload = MessagePayload(
        i18n_key="start_msg", i18n_kwargs=i18n_kwargs, reply_markup=ReplyKeyboard.main(user_dto)
    )
    await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("decline"))
@router.message(I18nTextFilter("command_cancel"))
@router.message(Command("cancel"))
async def cmd_cancel_state(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
):
    current_state = await state.get_state()
    if current_state:
        await state.clear()

    payload = MessagePayload(i18n_key="state_reset", reply_markup=ReplyKeyboard.main(user_dto))
    await notifier.notify_user(user_dto, payload=payload)
