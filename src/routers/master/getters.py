from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from core.i18n_translator import Translator


@inject
async def get_error_text(
    dialog_manager: DialogManager,
    translator: FromDishka[Translator],
    **kwargs,
):
    something_wrong_i18n_key = dialog_manager.dialog_data.pop("something_wrong", None)
    return {"error": translator.translate(something_wrong_i18n_key)}