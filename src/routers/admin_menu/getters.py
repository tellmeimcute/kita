

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from sqlalchemy.ext.asyncio import AsyncSession

from database.repository import SuggestionRepository, UserRepository, MediaRepository


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
