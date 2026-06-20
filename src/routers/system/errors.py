from logging import getLogger

from aiogram import F, Router, html
from aiogram.filters.exception import ExceptionTypeFilter
from aiogram.types import ErrorEvent, Message
from dishka import FromDishka
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    KitaValidationError,
    SQLSuggestionNotFoundError,
    SQLUserNotFoundError,
    UnsupportedPayload,
    UserImmuneError,
)
from core.schemas.message_payload import MessagePayload
from database.enums import SuggestionStatus
from services import NotifierService, SuggestionService

router = Router(name="errors")

logger = getLogger(name="kita.errors")


@router.error(ExceptionTypeFilter(SQLUserNotFoundError), F.update.message.as_("message"))
async def user_not_found(
    event: ErrorEvent,
    message: Message,
    notifier: FromDishka[NotifierService],
):
    caller_id = message.from_user.id
    e: SQLUserNotFoundError = event.exception
    i18n_kwargs = {"user_id": e.target_id}

    if e.i18n_kwargs:
        i18n_kwargs.update(e.i18n_kwargs)

    payload = MessagePayload(
        i18n_key="user_not_found",
        i18n_kwargs=i18n_kwargs,
        reply_markup=e.return_kb,
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)


@router.error(ExceptionTypeFilter(UserImmuneError), F.update.message.as_("message"))
async def user_is_immune(
    event: ErrorEvent,
    message: Message,
    notifier: FromDishka[NotifierService],
):
    caller_id = message.from_user.id
    e: UserImmuneError = event.exception

    payload = MessagePayload(
        i18n_key="error_user_immune",
        reply_markup=e.return_kb,
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)


@router.error(ExceptionTypeFilter(SQLSuggestionNotFoundError), F.update.message.as_("message"))
async def suggestion_not_found(
    event: ErrorEvent,
    message: Message,
    notifier: FromDishka[NotifierService],
):
    caller_id = message.from_user.id
    e: SQLSuggestionNotFoundError = event.exception

    i18n_kwargs = {"suggestion_id": e.target_id}
    if e.i18n_kwargs:
        i18n_kwargs.update(e.i18n_kwargs)

    payload = MessagePayload(
        i18n_key="error_suggestion_not_found",
        i18n_kwargs=i18n_kwargs,
        reply_markup=e.return_kb,
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)


@router.error(ExceptionTypeFilter(KitaValidationError, ValidationError), F.update.message.as_("message"))
async def validation_error(
    event: ErrorEvent,
    message: Message,
    notifier: FromDishka[NotifierService],
):
    caller_id = message.from_user.id
    e: KitaValidationError | ValidationError = event.exception

    logger.error(e, exc_info=True)
    is_kita_exc = isinstance(e, KitaValidationError)

    payload = MessagePayload(
        i18n_key="command_syntax_error",
        i18n_kwargs={"hint": html.code("Validation Error.")},
        reply_markup=e.return_kb if is_kita_exc else None,
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)


@router.error(ExceptionTypeFilter(UnsupportedPayload), F.update.message.as_("message"))
async def payload_error(
    event: ErrorEvent,
    message: Message,
    session: FromDishka[AsyncSession],
    notifier: FromDishka[NotifierService],
    suggestion_service: FromDishka[SuggestionService],
):
    caller_id = message.from_user.id
    e: UnsupportedPayload = event.exception

    logger.error(e, exc_info=True)

    suggestion_id = e.payload.suggestion_id
    if suggestion_id:
        async with session.begin():
            await suggestion_service.update_by_id(suggestion_id, status=SuggestionStatus.DECLINED)

    payload = MessagePayload(
        i18n_key="command_syntax_error",
        i18n_kwargs={"hint": html.code("Unsupported Payload")},
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)
