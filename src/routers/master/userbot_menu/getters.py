


from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from database.dto import UserDTO
from services import UserBotService
from interfaces import UnitOfWorkProtocol

@inject
async def owned_userbots(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    **kwargs,
):
    user_dto: UserDTO = dialog_manager.middleware_data.get("user_dto")
    async with uow.transaction():
        userbots = await userbot_service.get_by_owner_id(user_dto.user_id)

    return {"userbots": userbots}

@inject
async def get_selected_userbot(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    userbot_service: FromDishka[UserBotService],
    **kwargs,
):
    bot_id = dialog_manager.dialog_data.get("selected_bot_id")
    async with uow.transaction():
        userbot = await userbot_service.get(bot_id)

    return {"selected_userbot": userbot}