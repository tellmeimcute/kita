from database.enums import UserRole

from .role_change import RoleChangeUseCase


class PromoteUserUseCase(RoleChangeUseCase):
    """Makes the user an admin of the bot."""

    __slots__ = ()

    TARGET_ROLE = UserRole.ADMIN
