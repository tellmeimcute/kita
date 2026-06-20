import pytest
from core.exceptions import UserImmuneError
from database.enums import UserRole
from usecases.change_role import ChangeRoleUseCase


def _set_role_side_effect(dto, role):
    dto.role = role


@pytest.mark.asyncio
async def test_ban_normal_user(user_service_mock, config_mock, admin_dto):
    target_dto = admin_dto.model_copy(update={"user_id": 2, "role": UserRole.USER})
    user_service_mock.get.return_value = target_dto
    user_service_mock.set_role.side_effect = _set_role_side_effect

    usecase = ChangeRoleUseCase(config=config_mock, user_service=user_service_mock)
    result = await usecase.execute(target_id=2, target_role=UserRole.BANNED, caller=admin_dto)

    user_service_mock.set_role.assert_awaited_once_with(target_dto, UserRole.BANNED)
    user_service_mock.decline_suggestion.assert_awaited_once_with(target_dto)
    assert result.role == UserRole.BANNED


@pytest.mark.asyncio
async def test_promote_to_admin(user_service_mock, config_mock, admin_dto):
    target_dto = admin_dto.model_copy(update={"user_id": 3, "role": UserRole.USER})
    user_service_mock.get.return_value = target_dto
    user_service_mock.set_role.side_effect = _set_role_side_effect

    usecase = ChangeRoleUseCase(config=config_mock, user_service=user_service_mock)
    result = await usecase.execute(target_id=3, target_role=UserRole.ADMIN, caller=admin_dto)

    user_service_mock.set_role.assert_awaited_once_with(target_dto, UserRole.ADMIN)
    user_service_mock.decline_suggestion.assert_not_called()
    assert result.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_cannot_ban_immune_admin(user_service_mock, config_mock, admin_dto):
    usecase = ChangeRoleUseCase(config=config_mock, user_service=user_service_mock)

    with pytest.raises(UserImmuneError):
        await usecase.execute(target_id=1, target_role=UserRole.BANNED, caller=admin_dto)

    user_service_mock.set_role.assert_not_called()


@pytest.mark.asyncio
async def test_cannot_ban_self(user_service_mock, config_mock, admin_dto):
    caller = admin_dto.model_copy(update={"user_id": 5})
    usecase = ChangeRoleUseCase(config=config_mock, user_service=user_service_mock)

    with pytest.raises(UserImmuneError):
        await usecase.execute(target_id=5, target_role=UserRole.BANNED, caller=caller)

    user_service_mock.set_role.assert_not_called()
