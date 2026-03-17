

from aiogram import Router, html
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from pydantic import ValidationError

from database.dto import UserDTO
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleData, IDCommand
from services import NotifierService, UserService
from handlers.keyboards import get_cancel_kb, get_admin_kb
from handlers.state import CommandBanState

from helpers.enums import BanAdminAction

router = Router()

@router.message(TextArgsFilter("command_ban_filter", IDCommand, action=BanAdminAction.BAN))
@router.message(TextArgsFilter("command_unban_filter", IDCommand, action=BanAdminAction.UNBAN))
async def ban_user_id_handler(
    message: Message,
    user_dto: UserDTO,
    command: IDCommand,
    notifier: NotifierService,
    user_service: UserService,
    action: BanAdminAction,
):
    target_role = "BANNED" if action == BanAdminAction.BAN else "USER"
    try:
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
            target_role=target_role,
            caller_dto=user_dto,
            notifier=notifier,
        )
        await user_service.change_role(cmd_data, notify_user=False)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)

@router.message(I18nTextFilter("command_ban_filter", action=BanAdminAction.BAN))
@router.message(I18nTextFilter("command_unban_filter", action=BanAdminAction.UNBAN))
async def ban_user_state_start(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: NotifierService,
    action: BanAdminAction
):
    payload = MessagePayload(i18n_key="state_wait_for_id", reply_markup=get_cancel_kb())
    await notifier.notify_user(user_dto, payload)
    await state.set_state(CommandBanState.wait_for_id)

    state_data = {"action": action}
    await state.set_data(state_data)

@router.message(CommandBanState.wait_for_id)
async def ban_user_state(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    notifier: NotifierService,
    user_service: UserService,
):
    data = await state.get_data()
    action = data.get("action")
    target_role = "BANNED" if action == BanAdminAction.BAN else "USER"

    try:
        cmd_data = ChangeRoleData(
            target_id=message.text,
            target_role=target_role,
            caller_dto=user_dto,
            notifier=notifier,
        )
        await user_service.change_role(cmd_data, notify_user=False, return_kb=get_admin_kb())
        await state.clear()
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)
