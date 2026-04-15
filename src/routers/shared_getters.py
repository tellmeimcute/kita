

from typing import Literal
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import Whenable

from database.dto import UserDTO
from database.roles import UserRole


def role_condition(
    role: UserRole,
    user_key: str,
    mode: Literal["not", "is"] = "is",
    data_source: Literal["dialog_data", "middleware_data"] = "dialog_data",
):
    def _factory(data: dict, widget: Whenable, manager: DialogManager):
        source: dict = getattr(manager, data_source)
        target_dto = source.get(user_key)

        if isinstance(target_dto, UserDTO):
            target_role = target_dto.role
        else:
            target_role = target_dto["role"]

        if mode == "is":
            return target_role == role
        if mode == "not":
            return target_role != role
    return _factory


is_admin = role_condition(UserRole.ADMIN, user_key="user_dto", data_source="middleware_data")