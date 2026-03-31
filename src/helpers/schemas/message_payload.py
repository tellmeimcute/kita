from typing import Any, Optional

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.media_group import MediaType
from .base import BaseData

AnyKeyboard = ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove
AnyContent = str | list[MediaType]


class MessagePayload(BaseData):
    i18n_key: Optional[str] = None
    i18n_kwargs: dict[str, Any] = {}

    reply_markup: Optional[AnyKeyboard] = None
    content: Optional[AnyContent] = None

    auto_delete_after: Optional[int] = 10