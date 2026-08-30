from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from database.dto import UserBotStats
from interfaces import UserBotStatsRepositoryProtocol


@inject
async def get_app_stats(
    dialog_manager: DialogManager,
    app_stats: FromDishka[UserBotStatsRepositoryProtocol],
    **kwargs,
):
    stats: UserBotStats = await app_stats.get()

    return {"userbot_stats": stats}
