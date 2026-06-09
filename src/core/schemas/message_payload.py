from typing import Any
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.media_group import MediaType
from .base import BaseData

AnyKeyboard = ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove

class MessagePayload(BaseData):
    i18n_key: str | None = None
    i18n_kwargs: dict[str, Any] = {}

    reply_markup: AnyKeyboard | None = None
    mediagroup: list[MediaType] | None = None

    suggestion_id: int | None = None