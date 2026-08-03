from typing import Literal

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable

from database.dto import UserProfileDTO
from database.enums import UserRole


def role_condition(
    role: UserRole,
    user_key: str,
    mode: Literal["not", "is"] = "is",
    data_source: Literal["dialog_data", "middleware_data"] = "dialog_data",
):
    def _factory(data: dict, widget: Whenable, manager: DialogManager):
        source: dict = getattr(manager, data_source)
        target_dto = source.get(user_key)

        if isinstance(target_dto, UserProfileDTO):
            target_role = target_dto.role
        elif isinstance(target_dto, dict):
            target_role = target_dto.get("role")
        else:
            return False

        if mode == "is":
            return target_role == role
        if mode == "not":
            return target_role != role

    return _factory


is_admin = role_condition(UserRole.ADMIN, user_key="profile_dto", data_source="middleware_data")
