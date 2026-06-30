


from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from core.i18n_translator import Translator


@inject
async def banner_text_getter(
    dialog_manager: DialogManager,
    translator: FromDishka[Translator],
    **kwargs,
):
    if dialog_manager.dialog_data.pop("something_wrong", False):
        text = translator.translate("banner_wait_for_text_again")
    else:
        text = translator.translate("banner_wait_for_text")
        
    return {"banner_text": text}
