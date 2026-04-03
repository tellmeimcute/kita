from aiogram import Router, html
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from routers.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand
from helpers.exceptions import UserImmuneError, SQLModelNotFoundError

from services import NotifierService, UserService

router = Router()


@router.message(I18nTextFilter("command_admin_help"))
async def admin_help(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
):
    payload = MessagePayload(i18n_key="admin_help_msg")
    await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("command_get_admin_menu"))
async def get_admin_menu(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
):
    payload = MessagePayload(i18n_key="success", reply_markup=ReplyKeyboard.admin_menu())
    await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("command_post_banner"))
async def post_channel_banner(
    message: Message,
    user_dto: UserDTO,
    config: Config,
    notifier: NotifierService,
):
    runtime_config = config.runtime_config

    builder = InlineKeyboardBuilder()
    builder.button(text="Предложка", url=runtime_config.bot_url)

    payload = MessagePayload(i18n_key="channel_banner", reply_markup=builder.as_markup())
    await notifier.send(config.CHANNEL_ID, payload)

    payload = MessagePayload(i18n_key="channel_banner_sent")
    await notifier.notify_user(user_dto, payload)


@router.message(TextArgsFilter("command_change_role", ChangeRoleCommand))
async def change_user_role(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    notifier: NotifierService,
    command: ChangeRoleCommand,
    user_service: UserService,
):
    try:
        target_new_kb = ReplyKeyboard.main_by_role(command.target_role)

        if command.target_id == user_dto.user_id:
            raise UserImmuneError()
         
        async with session.begin():
            target_dto = await user_service.get(command.target_id)
            await user_service.set_role(target_dto, command.target_role)
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
        await notifier.notify_user(user_dto, payload)
    except SQLModelNotFoundError:
        i18n_kwargs = {"user_id": command.target_id}
        payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs)
        await notifier.notify_user(user_dto, payload)

    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )
    await notifier.notify_user(user_dto, payload)

    i18n_kwargs = {"role": command.target_role}
    payload = MessagePayload(
        i18n_key="notify_user_role_changed",
        i18n_kwargs=i18n_kwargs,
        reply_markup=target_new_kb,
    )
    await notifier.notify_user(target_dto, payload)


@router.message(I18nTextFilter("command_admin_stats"))
async def global_stats(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    notifier: NotifierService,
):
    suggestions_count = await SuggestionDAO.count(session)
    media_count = await MediaDAO.count(session)
    user_stats = await UserAlchemyDAO.get_users_stats(session)

    i18n_kwargs = user_stats._asdict()
    i18n_kwargs.update(suggestions=suggestions_count, medias=media_count)

    payload = MessagePayload(i18n_key="global_stats", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(user_dto, payload)
