from aiogram import Router, html
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from handlers.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand, ChangeRoleData
from services import NotifierService, UserService

from handlers.keyboards import ReplyKeyboard

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
    builder.button(
        text="Предложка", url=runtime_config.bot_url
    )

    payload = MessagePayload(i18n_key="channel_banner", reply_markup=builder.as_markup())
    await notifier.send_channel(config.CHANNEL_ID, payload)

    payload = MessagePayload(i18n_key="channel_banner_sent")
    await notifier.notify_user(user_dto, payload)

@router.message(TextArgsFilter("command_change_role", ChangeRoleCommand))
async def change_user_role(
    message: Message,
    user_dto: UserDTO,
    notifier: NotifierService,
    command: ChangeRoleCommand,
    user_service: UserService,
):    
    try:
        target_new_kb = ReplyKeyboard.main_by_role(command.target_role)
        cmd_data = ChangeRoleData(
            target_id=command.target_id,
            target_role=command.target_role,
            caller_dto=user_dto,
            notifier=notifier,
            target_new_kb=target_new_kb,
        )
        await user_service.change_role(cmd_data)
    except (ValueError, ValidationError):
        payload = MessagePayload(
            i18n_key="command_syntax_error",
            i18n_kwargs={"hint": html.code("COMMAND USERID[int] ROLE[str]")},
        )
        await notifier.notify_user(user_dto, payload)

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