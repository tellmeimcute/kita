


from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from core.i18n_translator import Translator


@inject
async def user_select_getter(
    dialog_manager: DialogManager,
    translator: FromDishka[Translator],
    **kwargs,
):
    if dialog_manager.dialog_data.pop("user_not_found", False):
        text = translator.translate("user_not_found_wait_next_id")
    else:
        text = translator.translate("wait_user_id_text")
        
    return {"user_select_text": text}
