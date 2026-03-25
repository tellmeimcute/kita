
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from pydantic import ValidationError

from database.dto import UserDTO
from database.roles import UserRole
from handlers.keyboards import ReplyKeyboard
from handlers.state import CommandBanState
from helpers.enums import BanAdminAction
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import IDCommand
from helpers.exceptions import UserImmuneError, SQLModelNotFoundError
from services import NotifierService, UserService

router = Router()


@router.message(TextArgsFilter("command_ban_filter", IDCommand, action=BanAdminAction.BAN))
@router.message(TextArgsFilter("command_unban_filter", IDCommand, action=BanAdminAction.UNBAN))
async def ban_user_id_handler(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    command: IDCommand,
    notifier: NotifierService,
    user_service: UserService,
    action: BanAdminAction,
):
    target_role = UserRole.BANNED if action == BanAdminAction.BAN else UserRole.USER
    try:
        if command.target_id == user_dto.user_id:
            raise UserImmuneError()
        
        async with session.begin():
            target_dto = await user_service.get(command.target_id)
            await user_service.set_role(target_dto, target_role)
            if target_dto.is_banned:
                await user_service.decline_suggestion(target_dto)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)
    except UserImmuneError:
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)
    except SQLModelNotFoundError:
        i18n_kwargs = {"user_id": command.target_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)

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
    notifier: NotifierService,
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
    notifier: NotifierService,
    user_service: UserService,
):
    data = await state.get_data()
    action = data.get("action")
    target_role = UserRole.BANNED if action == BanAdminAction.BAN else UserRole.USER
    await state.clear()

    try:
        if message.text == user_dto.user_id:
            raise UserImmuneError()
        
        async with session.begin():
            target_dto = await user_service.get(message.text)
            await user_service.set_role(target_dto, target_role)
            if target_dto.is_banned:
                await user_service.decline_suggestion(target_dto)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("Validation Error.")},
        )
        return await notifier.notify_user(user_dto, payload)
    except UserImmuneError:
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)
    except SQLModelNotFoundError:
        i18n_kwargs = {"user_id": message.text}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        return await notifier.notify_user(user_dto, payload)
    
    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )
    await notifier.notify_user(user_dto, payload)
