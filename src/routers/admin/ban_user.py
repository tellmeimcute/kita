
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError

from dishka import FromDishka

from database.dto import UserDTO
from database.roles import UserRole
from ui.keyboards import ReplyKeyboard
from routers.state import CommandBanState
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload
from helpers.schemas import IDCommand
from core.enums import BanAdminAction
from core.exceptions import KitaValidationError
from core.exceptions.base import KitaException
from services import NotifierService, UserService

router = Router()


@router.message(TextArgsFilter("command_ban_filter", IDCommand, action=BanAdminAction.BAN))
@router.message(TextArgsFilter("command_unban_filter", IDCommand, action=BanAdminAction.UNBAN))
async def ban_user_id_handler(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    command: IDCommand,
    notifier: FromDishka[NotifierService],
    user_service: UserService,
    action: BanAdminAction,
):
    target_role = UserRole.BANNED if action == BanAdminAction.BAN else UserRole.USER

    async with session.begin():
        target_dto = await user_service.moderate_user(
            command.target_id, target_role, caller=user_dto
        )

    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )

    await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("command_ban_filter", action=BanAdminAction.BAN))
@router.message(I18nTextFilter("command_unban_filter", action=BanAdminAction.UNBAN))
async def ban_user_state_start(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    action: BanAdminAction,
):
    payload = MessagePayload(i18n_key="state_wait_for_id", reply_markup=ReplyKeyboard.cancel())
    await notifier.notify_user(user_dto, payload)
    await state.set_state(CommandBanState.wait_for_id)

    state_data = {"action": action}
    await state.set_data(state_data)


@router.message(CommandBanState.wait_for_id)
async def ban_user_state(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
    user_service: UserService,
):
    data = await state.get_data()
    action = data.get("action")
    target_role = UserRole.BANNED if action == BanAdminAction.BAN else UserRole.USER
    
    await state.clear()

    return_kb = ReplyKeyboard.admin_menu()
    try:
        command = IDCommand(target_id=message.text)

        async with session.begin():
            target_dto = await user_service.moderate_user(
                command.target_id, target_role, caller=user_dto
            )

        payload = MessagePayload(
            i18n_key="answer_admin_role_changed",
            i18n_kwargs=target_dto.model_dump(),
            reply_markup=return_kb,
        )

        await notifier.notify_user(user_dto, payload)
    except ValidationError as e:
        exc = KitaValidationError(pydantic_exc=e, return_kb=return_kb)
        raise exc
    except KitaException as e:
        e.return_kb = return_kb
        raise e
