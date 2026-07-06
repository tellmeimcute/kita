
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram import html

from aiogram_dialog import DialogManager

from core.config import RuntimeConfig
from core.i18n_translator import Translator
from interfaces import SuggestionServiceProtocol
from database.dto import UserDTO


@inject
async def get_menu_i18n_kwargs(
    dialog_manager: DialogManager,
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    runtime_config: FromDishka[RuntimeConfig],
    translator: FromDishka[Translator],
    **kwargs
):
    user_dto: UserDTO = dialog_manager.middleware_data.get("user_dto")

    stats = await suggestion_service.get_user_stats(user_dto)
    i18n_kwargs = stats.model_dump()

    stats_text = translator.i18n_text(i18n_key="user_stats", i18n_kwargs=i18n_kwargs)
    signature = "Anonymous" if user_dto.prefer_anonymous else user_dto.name

    return {
        "stats_text": stats_text,
        "user_stats": i18n_kwargs,
        "signature": signature,
        "channel_name": runtime_config.channel_name,
    }
