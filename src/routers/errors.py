from logging import getLogger
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Router, F, html
from aiogram.types import Message, ErrorEvent
from aiogram.filters.exception import ExceptionTypeFilter

from dishka import FromDishka

from helpers.schemas.message_payload import MessagePayload
from core.exceptions import (
    SQLUserNotFoundError,
    SQLSuggestionNotFoundError,
    UserImmuneError,
    KitaValidationError,
    UnsupportedPayload,
)
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

    if e.payload.suggestion_id:
        async with session.begin():
            await suggestion_service.dao.update_by_id(
                session, e.payload.suggestion_id, {"accepted": False}
            )

    payload = MessagePayload(
        i18n_key="command_syntax_error",
        i18n_kwargs={"hint": html.code("Unsupported Payload")},
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)