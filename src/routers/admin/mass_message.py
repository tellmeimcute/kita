import asyncio
from itertools import batched
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, MessageOriginChannel

from database.dto import UserDTO
from routers.keyboards import ReplyKeyboard
from routers.state import MassMessageState
from helpers.filters import I18nTextFilter
from helpers.message_payload import MessagePayload
from helpers.schemas.data import MassMessageData
from services import NotifierService, UserService

router = Router()


async def mass_message_task(
    notifier: NotifierService, data: MassMessageData, status_message: Message
):
    send_func = notifier.forward_messages if data.is_forwarded else notifier.copy_messages
    for chunk in batched(data.users, notifier.chunk_size):
        tasks = [
            send_func(user_dto, data.source_message_ids, data.source_chat_id) for user_dto in chunk
        ]
        result = await asyncio.gather(*tasks)
        success = [r for r in result if r]
        data = data.model_copy(
            update={
                "progress": data.progress + len(result),
                "success": data.success + len(success),
                "failure": data.failure + len(result) - len(success),
            }
        )

        if data.progress % 10 == 0 or data.progress == len(data.users):
            i18n_kwargs = data.model_dump()
            i18n_kwargs["status"] = notifier.translator.get_translated_text(
                i18n_key="completed" if data.status else "in_process"
            )
            new_status = notifier.translator.get_i18n_text("mass_message_status", i18n_kwargs)
            await notifier.edit_message(status_message, new_status)
    
        await asyncio.sleep(notifier.chunk_delay)

@router.message(I18nTextFilter("command_mass_message"))
async def mass_message_start(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    notifier: NotifierService,
    user_service: UserService,
    state: FSMContext,
):
    await state.set_state(MassMessageState.wait_for_message)

    async with session.begin():
        active = await user_service.get_active()

    data = MassMessageData(users=active)

    await state.update_data(mass_message_data=data.model_dump())

    payload = MessagePayload(
        i18n_key="mass_message_wait_for_text",
        i18n_kwargs=data.model_dump(),
        reply_markup=ReplyKeyboard.cancel(),
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
            "is_forwarded": True
            if isinstance(message.forward_origin, MessageOriginChannel)
            else False,
            "source_chat_id": message.chat.id,
            "source_message_ids": [m.message_id for m in album],
        }
    )

    await state.update_data(mass_message_data=data.model_dump())

    i18n_kwargs = data.model_dump()
    estimated_time = (data.users_count / notifier.chunk_size) * notifier.chunk_delay
    i18n_kwargs.update({"estimated_time": int(estimated_time)})

    payload = MessagePayload(
        i18n_key="mass_message_confirm",
        i18n_kwargs=i18n_kwargs,
        reply_markup=ReplyKeyboard.confirm_decline(),
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
    state_data = await state.get_data()
    raw_data = state_data.get("mass_message_data")
    data = MassMessageData.model_validate(raw_data)

    payload = MessagePayload(
        i18n_key="mass_message_started", reply_markup=ReplyKeyboard.main(user_dto)
    )
    await notifier.notify_user(user_dto, payload)

    i18n_kwargs = data.model_dump()
    i18n_kwargs["status"] = notifier.translator.get_translated_text(
        i18n_key="completed" if data.status else "in_process"
    )
    payload = MessagePayload(
        i18n_key="mass_message_status",
        i18n_kwargs=i18n_kwargs,
    )
    status_message = await notifier.notify_user(user_dto, payload)

    asyncio.create_task(mass_message_task(notifier, data, status_message))
    await state.clear()
