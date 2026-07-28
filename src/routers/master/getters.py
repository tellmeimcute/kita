from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from core.i18n_translator import Translator


@inject
async def bot_token_window_text(
    dialog_manager: DialogManager,
    translator: FromDishka[Translator],
    **kwargs,
):
    something_wrong_i18n_key = dialog_manager.dialog_data.pop("something_wrong", None)

    if something_wrong_i18n_key:
        text = translator.translate(something_wrong_i18n_key)
    else:
        text = translator.translate("reg_bot_wait_for_token")
        
    return {"text": text}