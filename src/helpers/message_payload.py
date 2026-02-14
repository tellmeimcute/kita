from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.media_group import MediaGroupBuilder, MediaType

AnyKeyboard = ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove
AnyContent = str | list[MediaType]


class MessagePayload(BaseModel):
    i18n_key: Optional[str] = None
    i18n_kwargs: dict[str, Any] = {}

    reply_markup: Optional[AnyKeyboard] = None
    content: Optional[AnyContent] = None

    auto_delete_after: Optional[int] = 10

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
