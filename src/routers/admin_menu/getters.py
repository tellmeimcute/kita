

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.data import MassMessageData
from database.repository import SuggestionRepository, UserRepository, MediaRepository
from usecases.broadcast import BroadcastUseCase


@inject
async def get_app_stats(
    dialog_manager: DialogManager,
    session: FromDishka[AsyncSession],
    s_repo: FromDishka[SuggestionRepository],
    u_repo: FromDishka[UserRepository],
    m_repo: FromDishka[MediaRepository],
    **kwargs
):
    user_stats = await u_repo.user_stats()
    suggestions_count = await s_repo.count()
    media_count = await m_repo.count()

    i18n_kwargs = user_stats._asdict()
    i18n_kwargs.update(suggestions=suggestions_count, medias=media_count)

    return i18n_kwargs


@inject
async def get_broadcast_info(
    dialog_manager: DialogManager,
    broadcast: FromDishka[BroadcastUseCase],
    **kwargs
):
    data_raw = dialog_manager.dialog_data.get("broadcast_data")
    broadcast_data = MassMessageData.model_validate(data_raw)

    estimated_time = broadcast.estimate_time(broadcast_data)
    return {
        "users_count": broadcast_data.users_count,
        "estimated_time": estimated_time,
    }