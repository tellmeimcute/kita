from aiogram import Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka

from core.config import Config, RuntimeConfig
from database.dao import MediaDAO, SuggestionDAO, UserAlchemyDAO
from database.dto import UserDTO
from ui.keyboards import ReplyKeyboard
from helpers.filters import I18nTextFilter, TextArgsFilter
from helpers.schemas.message_payload import MessagePayload
from helpers.schemas import ChangeRoleCommand

from services import NotifierService, UserService

router = Router()


@router.message(I18nTextFilter("command_get_admin_menu"))
async def get_admin_menu(
    message: Message,
    user_dto: UserDTO,
    notifier: FromDishka[NotifierService],
):
    payload = MessagePayload(i18n_key="success", reply_markup=ReplyKeyboard.admin_menu())
    await notifier.notify_user(user_dto, payload)


@router.message(I18nTextFilter("command_post_banner"))
async def post_channel_banner(
    message: Message,
    user_dto: UserDTO,
    config: Config,
    notifier: FromDishka[NotifierService],
    runtime_config: FromDishka[RuntimeConfig]
):
    builder = InlineKeyboardBuilder()
    builder.button(text="Предложка", url=runtime_config.bot_url)

    payload = MessagePayload(i18n_key="channel_banner", reply_markup=builder.as_markup())
    strategy = notifier.send_strategy_factory(config.CHANNEL_ID, payload)
    await notifier.send(strategy)

    payload = MessagePayload(i18n_key="channel_banner_sent")
    await notifier.notify_user(user_dto, payload)


@router.message(TextArgsFilter("command_change_role", ChangeRoleCommand))
async def change_user_role(
    message: Message,
    user_dto: UserDTO,
    session: AsyncSession,
    notifier: FromDishka[NotifierService],
    command: ChangeRoleCommand,
    user_service: UserService,
):
    async with session.begin():
        target_dto = await user_service.moderate_user(
            command.target_id, command.target_role, caller=user_dto
        )

    payload = MessagePayload(
        i18n_key="answer_admin_role_changed",
        i18n_kwargs=target_dto.model_dump(),
    )
    await notifier.notify_user(user_dto, payload)

    i18n_kwargs = {"role": command.target_role}
    target_new_kb = ReplyKeyboard.main_by_role(command.target_role)
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
    notifier: FromDishka[NotifierService],
):
    suggestions_count = await SuggestionDAO.count(session)
    media_count = await MediaDAO.count(session)
    user_stats = await UserAlchemyDAO.get_users_stats(session)

    i18n_kwargs = user_stats._asdict()
    i18n_kwargs.update(suggestions=suggestions_count, medias=media_count)

    payload = MessagePayload(i18n_key="global_stats", i18n_kwargs=i18n_kwargs)
    await notifier.notify_user(user_dto, payload)
