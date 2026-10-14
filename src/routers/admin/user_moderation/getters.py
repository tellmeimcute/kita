from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.i18n_translator import Translator
from database.enums import UserRole
from interfaces import UnitOfWorkProtocol, UserProfileServiceProtocol, UserServiceProtocol

DEFAULT_USER_FILTER = "all"

USER_FILTERS: dict[str, dict] = {
    "all": {},
    "users": {"role": UserRole.USER},
    "admins": {"role": UserRole.ADMIN},
    "banned": {"role": UserRole.BANNED},
    "blocked": {"bot_blocked": True},
}

USER_FILTER_LABEL_KEYS: dict[str, str] = {
    "all": "user_filter_all",
    "users": "user_filter_users",
    "admins": "user_filter_admins",
    "banned": "user_filter_banned",
    "blocked": "user_filter_blocked",
}


@inject
async def get_userbot_user_profiles(
    dialog_manager: DialogManager,
    uow: FromDishka[UnitOfWorkProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    translator: FromDishka[Translator],
    **kwargs,
):
    filter_key = dialog_manager.dialog_data.get("user_filter", DEFAULT_USER_FILTER)
    if filter_key not in USER_FILTERS:
        filter_key = DEFAULT_USER_FILTER

    async with uow.transaction():
        profiles = await profile_service.get_many(
            limit=50,
            order_desc=True,
            **USER_FILTERS[filter_key],
        )

    return {
        "profiles": profiles,
        "filter_label": translator.translate(USER_FILTER_LABEL_KEYS[filter_key]),
    }


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
