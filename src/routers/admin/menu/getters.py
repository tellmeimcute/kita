

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from interfaces import UnitOfWorkProtocol

@inject
async def get_app_stats(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    **kwargs
):
    user_stats = await uow.users.user_stats()
    suggestions_count = await uow.suggestions.count()
    media_count = await uow.medias.count()

    i18n_kwargs = user_stats._asdict()
    i18n_kwargs.update(suggestions=suggestions_count, medias=media_count)

    return i18n_kwargs
