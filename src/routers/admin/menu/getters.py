from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from database.dto import UserBotStats
from interfaces import UnitOfWorkProtocol


@inject
async def get_app_stats(
    dialog_manager: DialogManager, uow: FromDishka[UnitOfWorkProtocol], **kwargs
):
    user_stats = await uow.profiles.bot_user_stats()
    suggestions_count = await uow.suggestions.count()
    media_count = await uow.medias.count()
    user_stats = user_stats._asdict()

    stats = UserBotStats(
        users_total=user_stats["users_total"],
        users=user_stats["users"],
        banned=user_stats["banned"],
        admins=user_stats["admins"],
        suggestions=suggestions_count,
        medias=media_count,
    )

    return {"userbot_stats": stats}
