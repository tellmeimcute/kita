
from logging import getLogger
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import UserAlchemyDAO
from database.dto import UserDTO

from handlers.keyboards import get_main_kb_by_role

from helpers.schemas import ChangeRoleCommand
from helpers.message_payload import MessagePayload

logger = getLogger()

async def ban_user(
    session: AsyncSession,
    cmd_data: ChangeRoleCommand,
    notify_user: bool = True,
) -> bool | UserDTO:
    notifier = cmd_data.notifier
    caller_dto = cmd_data.caller_dto

    if cmd_data.target_id == cmd_data.bot_owner_id or cmd_data.target_id == caller_dto.user_id:
        payload = MessagePayload(i18n_key="error_user_immune")
        await notifier.notify_user(caller_dto, payload)
        return False

    try:
        async with session.begin():
            target_orm = await UserAlchemyDAO.change_role(session, cmd_data.target_id, cmd_data.target_role)
            target_dto = UserDTO.model_validate(target_orm)
    except KeyError:
        i18n_kwargs = {"user_id": cmd_data.target_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        await notifier.notify_user(caller_dto, payload)
        return False
    except Exception as e:
        return False

    # NOTIFY CALLER
    i18n_kwargs = {
        "username": target_dto.username,
        "user_id": target_dto.user_id,
        "role": target_dto.role,
    }
    payload = MessagePayload(i18n_key="answer_admin_role_changed", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(caller_dto, payload)

    # NOTIFY USER
    if notify_user:
        kb = get_main_kb_by_role(cmd_data.target_role)
        i18n_kwargs = {"role": cmd_data.target_role}
        payload = MessagePayload(
            i18n_key="notify_user_role_changed", i18n_kwargs=i18n_kwargs, reply_markup=kb
        )
        await notifier.notify_user(target_dto, payload)

    logger.info(
        "%s (%s) изменил роль пользователю %s (%s) на %s",
        caller_dto.username,
        caller_dto.user_id,
        target_dto.username,
        target_dto.user_id,
        target_dto.role,
    )

    return target_dto