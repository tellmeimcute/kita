from database.enums import UserRole

from .role_change import RoleChangeUseCase


class DemoteUserUseCase(RoleChangeUseCase):
    """Returns the user to the plain role (including an unban)."""

    __slots__ = ()

    TARGET_ROLE = UserRole.USER
