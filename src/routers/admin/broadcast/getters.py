

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.schemas.broadcast import BroadcastData
from usecases.broadcast import BroadcastUseCase


@inject
async def get_broadcast_info(
    dialog_manager: DialogManager,
    broadcast: FromDishka[BroadcastUseCase],
    **kwargs
):
    data_raw = dialog_manager.dialog_data.get("broadcast_data")
    broadcast_data = BroadcastData.model_validate(data_raw)

    estimated_time = broadcast.estimate_time(broadcast_data)
    return {
        "users_count": broadcast_data.users_count,
        "estimated_time": estimated_time,
    }

