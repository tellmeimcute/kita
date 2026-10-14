from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from interfaces import UnitOfWorkProtocol, UserProfileServiceProtocol, UserServiceProtocol


@inject
async def get_userbot_user_profiles(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    **kwargs,
):
    async with uow.transaction():
        profiles = await profile_service.get_many(limit=50, order_desc=True)
    return {"profiles": profiles}


@inject
async def get_selected_user(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    translator: FromDishka[Translator],
    **kwargs,
):
    user_id = dialog_manager.dialog_data.get("selected_user_id")
    if not user_id:
        return {"selected_user": None}

    user_id = int(user_id)

    async with uow.transaction():
        target_user = await user_service.get(user_id)
        target_profile = await profile_service.get(user_id)

    target_blocked = (
        translator.translate("user_blocked_bot") + "\n"
        if target_profile and target_profile.is_bot_blocked
        else ""
    )

    return {
        "target_dto": target_user,
        "target_profile": target_profile,
        "target_blocked": target_blocked,
    }
