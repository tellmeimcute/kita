
from typing import Sequence, Any

from sqlalchemy import Result, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserProfile, Suggestion
from database.dto import UserProfileDTO
from database.enums import UserRole, SuggestionStatus
from interfaces import BotRegistryProtocol

class UserProfileRepository:

    def __init__(
        self,
        session: AsyncSession,
        bot_registry: BotRegistryProtocol,
    ):
        self._session = session
        self._current_bot = bot_registry.get_current()

    async def get(self, user_id: int) -> UserProfileDTO | None:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.user_id == user_id,
                UserProfile.bot_id == self._current_bot.id,
            )
        )

        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()
        if not orm_model:
            return None
        return UserProfileDTO.model_validate(orm_model)

    async def get_or_create(self, user_id: int) -> UserProfileDTO:
        profile = await self.get(user_id)
        if profile:
            return profile

        profile = await self.create(user_id)
        return profile

    async def create(self, user_id: int) -> UserProfileDTO:
        orm = UserProfile(bot_id=self._current_bot.id, user_id=user_id)
        self._session.add(orm)
        await self._session.flush()
        return UserProfileDTO.model_validate(orm)

    async def update(self, user_id: int, **data: Any):
        stmt = (
            update(UserProfile)
            .where(
                UserProfile.user_id == user_id,
                UserProfile.bot_id == self._current_bot.id,
            )
            .values(data)
        )
        await self._session.execute(stmt)

    async def save(self, dto: UserProfileDTO):
        if changed := dto.prepare_changed_data():
            await self.update(dto.user_id, **changed)

    async def get_active(self) -> Sequence[UserProfileDTO]:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.bot_id == self._current_bot.id,
                (UserProfile.role != UserRole.BANNED) & UserProfile.is_bot_blocked.is_not(True),
            )
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserProfileDTO.from_model_list(orm_models)

    async def get_admins(self) -> Sequence[UserProfileDTO]:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.bot_id == self._current_bot.id,
                UserProfile.role == UserRole.ADMIN,
            )
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserProfileDTO.from_model_list(orm_models)

    async def get_banned(self) -> Sequence[UserProfileDTO]:
        stmt = (
            select(UserProfile)
            .where(
                UserProfile.bot_id == self._current_bot.id,
                UserProfile.role == UserRole.BANNED,
            )
        )

        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()
        return UserProfileDTO.from_model_list(orm_models)

    async def count(self) -> int:
        stmt = (
            select(func.count(UserProfile.id))
            .where(UserProfile.bot_id == self._current_bot.id)
        )
        count = await self._session.scalar(stmt)
        return count or 0

    async def admins_count(self) -> int:
        stmt = (
            select(func.count(UserProfile.id))
            .where(
                UserProfile.bot_id == self._current_bot.id,
                UserProfile.role == UserRole.ADMIN,
            )
        )
        count = await self._session.scalar(stmt)
        return count or 0

    async def banned_count(self) -> int:
        stmt = (
            select(func.count(UserProfile.id))
            .where(
                UserProfile.bot_id == self._current_bot.id,
                UserProfile.role == UserRole.BANNED,
            )
        )
        count = await self._session.scalar(stmt)
        return count or 0

    async def bot_user_stats(self):
        stmt = select(
            func.count(UserProfile.id).label("users_total"),
            func.count(UserProfile.id).filter(UserProfile.role == UserRole.USER).label("users"),
            func.count(UserProfile.id).filter(UserProfile.role == UserRole.ADMIN).label("admins"),
            func.count(UserProfile.id).filter(UserProfile.role == UserRole.BANNED).label("banned"),
        ).where(UserProfile.bot_id == self._current_bot.id)
        result: Result = await self._session.execute(stmt)
        return result.one()

    async def decline_all_suggestions(self, user_id: int):
        stmt = (
            update(Suggestion)
            .where(
                Suggestion.author_id == user_id,
                Suggestion.bot_id == self._current_bot.id,
            )
            .values(status=SuggestionStatus.DECLINED)
        )
        await self._session.execute(stmt)
