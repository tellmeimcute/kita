
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram import html

from aiogram_dialog import DialogManager

from core.config import RuntimeConfig
from core.i18n_translator import Translator

from database.dto import UserDTO
from services.suggestion import SuggestionService


@inject
async def get_statistic(
    dialog_manager: DialogManager,
    suggestion_service: FromDishka[SuggestionService],
    translator: FromDishka[Translator],
    **kwargs
):
    user_dto: UserDTO = dialog_manager.middleware_data.get("user_dto")

    stats = await suggestion_service.get_user_stats(user_dto)
    stats_text = translator.get_i18n_text(i18n_key="user_stats", i18n_kwargs=stats.model_dump())
    return {"stats_text": stats_text}

@inject
async def get_runtime_config(
    dialog_manager: DialogManager,
    runtime_config: FromDishka[RuntimeConfig],
    **kwargs
):
    i18n_kwargs = runtime_config.model_dump()
    i18n_kwargs.update({"channel_name": html.bold(runtime_config.channel_name)})
    return i18n_kwargs
