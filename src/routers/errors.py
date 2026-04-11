
from pydantic import ValidationError

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
)
from services import NotifierService

router = Router(name="errors")

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
    is_kita_exc = isinstance(e, KitaValidationError)

    payload = MessagePayload(
        i18n_key="command_syntax_error",
        i18n_kwargs={"hint": html.code("Validation Error.")},
        reply_markup=e.return_kb if is_kita_exc else None,
    )

    strategy = notifier.send_strategy_factory(caller_id, payload)
    await notifier.send(strategy)