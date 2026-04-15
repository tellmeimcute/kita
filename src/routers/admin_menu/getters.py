

from sqlalchemy.ext.asyncio import AsyncSession

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram_dialog import DialogManager
from database.dao import SuggestionDAO, MediaDAO, UserAlchemyDAO

from services.notifier import NotifierService
from helpers.schemas.data import MassMessageData



@inject
async def get_app_stats(dialog_manager: DialogManager, **kwargs):
    session: AsyncSession = dialog_manager.middleware_data.get("session")

    suggestions_count = await SuggestionDAO.count(session)
    media_count = await MediaDAO.count(session)
    user_stats = await UserAlchemyDAO.get_users_stats(session)

    i18n_kwargs = user_stats._asdict()
    i18n_kwargs.update(suggestions=suggestions_count, medias=media_count)

    return i18n_kwargs


@inject
async def get_broadcast_info(
    dialog_manager: DialogManager,
    notifier: FromDishka[NotifierService],
    **kwargs
):
    data_raw = dialog_manager.dialog_data.get("broadcast_data")
    broadcast_data = MassMessageData.model_validate(data_raw)
    
    estimated_time = (broadcast_data.users_count / notifier.chunk_size) * notifier.chunk_delay
    i18n_kwargs = {
        "users_count": broadcast_data.users_count,
        "estimated_time": estimated_time,
    }

    return i18n_kwargs