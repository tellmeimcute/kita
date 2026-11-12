from database.dto import UserBotDTO, UserDTO, UserProfileDTO
from database.enums import UserRole
from events import SuggestionDeclined, UserBanned
from interfaces import (
    EventBusProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
)

from .role_change import RoleChangeUseCase


class BanUserUseCase(RoleChangeUseCase):
    """Banning is more than a role: the pending suggestions go away with it."""

    __slots__ = ("_events", "_suggestions")

    TARGET_ROLE = UserRole.BANNED

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        user_profile_service: UserProfileServiceProtocol,
        suggestion_service: SuggestionServiceProtocol,
        userbot: UserBotDTO,
        events: EventBusProtocol,
    ):
        super().__init__(uow, user_profile_service, userbot)

        self._suggestions = suggestion_service
        self._events = events

    async def _apply(self, target_id: int, caller: UserDTO) -> UserProfileDTO:
        profile_dto = await super()._apply(target_id, caller)

        declined = await self._suggestions.decline_pending_by_author(target_id)
        for suggestion_id in declined:
            await self._events.publish(
                SuggestionDeclined(bot_id=self._userbot.bot_id, suggestion_id=suggestion_id)
            )

        await self._events.publish(
            UserBanned(
                bot_id=self._userbot.bot_id,
                user_id=profile_dto.user_id,
                admin_id=caller.user_id,
            )
        )

        return profile_dto
