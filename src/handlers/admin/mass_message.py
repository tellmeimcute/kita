
import asyncio
from aiogram import Router
from aiogram.types import Message, MessageOriginChannel
from aiogram.fsm.context import FSMContext

from database.dto import UserDTO
from handlers.state import MassMessageState
from handlers.keyboards import get_main_kb_by_role, get_confirm_decline_kb, get_cancel_kb
from helpers.filters import I18nTextFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import MassMessageData
from middlewares import MediaGroupMiddleware
from services import NotifierService, UserService

router = Router()
router.message.middleware(MediaGroupMiddleware(latency=0.25))

async def mass_message_task(notifier: NotifierService, data: MassMessageData, status_message: Message):
    send_func = (
        notifier.forward_messages
        if data.is_forwarded
        else notifier.copy_messages
    )

    for user in data.users:
        sended = await send_func(user, data.source_message_ids, data.source_chat_id)
        data = data.model_copy(update={
            "progress": data.progress + 1,
            "success": data.success + 1 if sended else data.success,
            "failure": data.failure + 1 if not sended else data.failure,
        })

        if data.progress % 10 == 0 or data.progress == len(data.users):
            i18n_kwargs = data.model_dump()
            i18n_kwargs["status"] = notifier.get_translated_text(i18n_key="completed" if data.status else "in_process")
            new_status = notifier.get_i18n_text("mass_message_status", i18n_kwargs)
            await notifier.edit_message(status_message, new_status)

        await asyncio.sleep(0.3)

@router.message(I18nTextFilter("command_mass_message"))
async def mass_message_start(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
    user_service: UserService,
    state: FSMContext,
):
    await state.set_state(MassMessageState.wait_for_message)

    active = await user_service.get_active()
    data = MassMessageData(users=active)

    await state.update_data(mass_message_data=data.model_dump())

    payload = MessagePayload(
        i18n_key="mass_message_wait_for_text",
        i18n_kwargs=data.model_dump(),
        reply_markup=get_cancel_kb(),
    )
    await notifier.notify_user(user_dto, payload)

@router.message(MassMessageState.wait_for_message)
async def mass_message_get_message(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
    state: FSMContext,
    media_group_id: int | None = None,
    album: list[Message] | None = None,
):
    state_data = await state.get_data()
    raw_data = state_data.get("mass_message_data")
    data = MassMessageData.model_validate(raw_data)

    if not album:
        album = (message,)

    data = data.model_copy(
        update={
            "is_forwarded": True if isinstance(message.forward_origin, MessageOriginChannel) else False,
            "source_chat_id": message.chat.id,
            "source_message_ids": [m.message_id for m in album]
        }
    )

    await state.update_data(mass_message_data=data)

    i18n_kwargs = data.model_dump()
    i18n_kwargs.update(
        {"estimated_time": data.users_count * 0.3}
    )

    payload = MessagePayload(
        i18n_key="mass_message_confirm",
        i18n_kwargs=i18n_kwargs,
        reply_markup=get_confirm_decline_kb(),
    )
    await notifier.notify_user(user_dto, payload)

    await state.set_state(MassMessageState.wait_confirm)

@router.message(MassMessageState.wait_confirm, I18nTextFilter("confirm"))
async def mass_message_confirm(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
    state: FSMContext,
):
    kb = get_main_kb_by_role(user_dto.role)

    state_data = await state.get_data()
    raw_data = state_data.get("mass_message_data")
    data = MassMessageData.model_validate(raw_data)

    payload = MessagePayload(i18n_key="mass_message_started", reply_markup=kb)
    await notifier.notify_user(user_dto, payload)

    i18n_kwargs = data.model_dump()
    i18n_kwargs["status"] = notifier.get_translated_text(i18n_key="completed" if data.status else "in_process")
    payload = MessagePayload(
        i18n_key="mass_message_status", 
        i18n_kwargs=i18n_kwargs,
    )
    status_message = await notifier.notify_user(user_dto, payload)

    asyncio.create_task(mass_message_task(notifier, data, status_message))
    await state.clear()