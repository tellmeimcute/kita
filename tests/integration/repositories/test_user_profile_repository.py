from unittest.mock import MagicMock

from core.schemas import MediaInfo
from database.enums import SuggestionStatus, UserRole

from ..readers import load_profile, load_suggestion
from ..scaffold import BOT_ID, FakeBotRegistry
from .conftest import RepositoryContext


async def create_user(ctx: RepositoryContext, *, offset: int = 1) -> int:
    user_id = ctx.test_user_dto.user_id + offset
    user_dto = ctx.test_user_dto.model_copy(
        update={"user_id": user_id, "username": f"profile_user_{offset}"}
    )

    async with ctx.uow.transaction():
        await ctx.user_repo.create(user_dto)

    return user_id


async def create_profile(
    ctx: RepositoryContext,
    *,
    offset: int = 1,
    role: UserRole = UserRole.USER,
    is_bot_blocked: bool = False,
) -> int:
    """Create user with profile."""
    user_id = await create_user(ctx, offset=offset)

    async with ctx.uow.transaction():
        await ctx.profile_repo.create(user_id)

        if role is not UserRole.USER or is_bot_blocked:
            await ctx.profile_repo.update(user_id, role=role, is_bot_blocked=is_bot_blocked)

    return user_id


async def create_suggestion(
    ctx: RepositoryContext,
    author_id: int,
    *,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> int:
    async with ctx.uow.transaction():
        created = await ctx.suggestion_repo.create(
            author_id=author_id,
            anonymous=False,
            mediainfo=[MediaInfo("photo", "photo-1")],
            caption="caption",
            media_group_id=None,
            forwarded_from=None,
        )

        if status is not SuggestionStatus.PENDING:
            await ctx.suggestion_repo.update(created.id, status=status)

    return created.id


async def test_create_returns_profile_with_user(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        created = await ctx.profile_repo.create(ctx.test_user_dto.user_id)

    assert created.user_id == ctx.test_user_dto.user_id
    assert created.bot_id == BOT_ID
    assert created.role is UserRole.USER
    assert created.is_bot_blocked is False
    assert created.user is not None
    assert created.user.name == ctx.test_user_dto.name

    row = await load_profile(ctx, created.user_id)

    assert row is not None
    assert row.bot_id == BOT_ID


async def test_get_by_id_returns_profile_with_user(repository_context: RepositoryContext):
    ctx = repository_context
    user_id = await create_profile(ctx)

    profile = await ctx.profile_repo.get_by_id(user_id)

    assert profile is not None
    assert profile.user_id == user_id
    assert profile.user is not None
    assert profile.user.username == "profile_user_1"


async def test_get_by_id_returns_none_for_user_without_profile(
    repository_context: RepositoryContext,
):
    ctx = repository_context

    profile = await ctx.profile_repo.get_by_id(ctx.test_user_dto.user_id)

    assert profile is None


async def test_get_by_id_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
    foreign_bot: MagicMock,
):
    ctx = repository_context
    user_id = await create_profile(ctx)

    async with bot_registry.with_bot(foreign_bot.id):
        assert await ctx.profile_repo.get_by_id(user_id) is None
        assert await ctx.profile_repo.count() == 0


async def test_get_or_create_creates_profile_once(repository_context: RepositoryContext):
    ctx = repository_context
    user_id = await create_user(ctx)

    async with ctx.uow.transaction():
        first = await ctx.profile_repo.get_or_create(user_id)

    async with ctx.uow.transaction():
        second = await ctx.profile_repo.get_or_create(user_id)

    assert first.user_id == second.user_id
    assert first.created_at == second.created_at
    assert await ctx.profile_repo.count() == 1


async def test_get_or_create_returns_created_profile(repository_context: RepositoryContext):
    ctx = repository_context
    user_id = await create_user(ctx)

    async with ctx.uow.transaction():
        created = await ctx.profile_repo.get_or_create(user_id)

    assert created.user_id == user_id
    assert created.role is UserRole.USER
    assert created.user is not None


async def test_update_persists_changes(repository_context: RepositoryContext):
    ctx = repository_context
    user_id = await create_profile(ctx)

    async with ctx.uow.transaction():
        await ctx.profile_repo.update(
            user_id,
            role=UserRole.ADMIN,
            is_bot_blocked=True,
            prefer_anonymous=True,
        )

    row = await load_profile(ctx, user_id)

    assert row.role is UserRole.ADMIN
    assert row.is_bot_blocked is True
    assert row.prefer_anonymous is True


async def test_update_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
    foreign_bot: MagicMock,
):
    ctx = repository_context
    user_id = await create_profile(ctx)

    async with bot_registry.with_bot(foreign_bot.id), ctx.uow.transaction():
        await ctx.profile_repo.update(user_id, role=UserRole.BANNED)

    row = await load_profile(ctx, user_id)

    assert row.role is UserRole.USER


async def test_get_many_pages_and_orders(repository_context: RepositoryContext):
    ctx = repository_context
    user_ids = [await create_profile(ctx, offset=offset) for offset in (1, 2, 3)]

    first_page = await ctx.profile_repo.get_many(limit=2)
    second_page = await ctx.profile_repo.get_many(limit=2, offset=2)
    reversed_page = await ctx.profile_repo.get_many(order_desc=True)

    assert [profile.user_id for profile in first_page] == user_ids[:2]
    assert [profile.user_id for profile in second_page] == user_ids[2:]
    assert [profile.user_id for profile in reversed_page] == user_ids[::-1]


async def test_get_many_filters_by_role(repository_context: RepositoryContext):
    ctx = repository_context
    admin_id = await create_profile(ctx, offset=1, role=UserRole.ADMIN)
    await create_profile(ctx, offset=2)

    admins = await ctx.profile_repo.get_many(role=UserRole.ADMIN)

    assert [profile.user_id for profile in admins] == [admin_id]


async def test_get_many_filters_by_bot_blocked(repository_context: RepositoryContext):
    ctx = repository_context
    blocked_id = await create_profile(ctx, offset=1, is_bot_blocked=True)
    await create_profile(ctx, offset=2)

    blocked = await ctx.profile_repo.get_many(bot_blocked=True)

    assert [profile.user_id for profile in blocked] == [blocked_id]


async def test_get_active_skips_banned_and_blocked(repository_context: RepositoryContext):
    ctx = repository_context
    active_id = await create_profile(ctx, offset=1)
    await create_profile(ctx, offset=2, role=UserRole.BANNED)
    await create_profile(ctx, offset=3, is_bot_blocked=True)

    active = await ctx.profile_repo.get_active()

    assert [profile.user_id for profile in active] == [active_id]


async def test_get_admins(repository_context: RepositoryContext):
    ctx = repository_context
    admin_id = await create_profile(ctx, offset=1, role=UserRole.ADMIN)
    await create_profile(ctx, offset=2)

    admins = await ctx.profile_repo.get_admins()

    assert [profile.user_id for profile in admins] == [admin_id]
    assert admins[0].user is not None
    assert admins[0].user.user_id == admin_id


async def test_get_banned(repository_context: RepositoryContext):
    ctx = repository_context
    banned_id = await create_profile(ctx, offset=1, role=UserRole.BANNED)
    await create_profile(ctx, offset=2)

    banned = await ctx.profile_repo.get_banned()

    assert [profile.user_id for profile in banned] == [banned_id]


async def test_demote_admins_keeps_owner(repository_context: RepositoryContext):
    ctx = repository_context
    owner_id = await create_profile(ctx, offset=1, role=UserRole.ADMIN)
    admin_id = await create_profile(ctx, offset=2, role=UserRole.ADMIN)
    user_id = await create_profile(ctx, offset=3)

    async with ctx.uow.transaction():
        demoted = await ctx.profile_repo.demote_admins(owner_id)

    assert list(demoted) == [admin_id]
    assert (await load_profile(ctx, owner_id)).role is UserRole.ADMIN
    assert (await load_profile(ctx, admin_id)).role is UserRole.USER
    assert (await load_profile(ctx, user_id)).role is UserRole.USER


async def test_counts_report_only_current_bot(repository_context: RepositoryContext):
    ctx = repository_context
    active_ids = [await create_profile(ctx, offset=1), await create_profile(ctx, offset=2)]
    admin_ids = [await create_profile(ctx, offset=3, role=UserRole.ADMIN)]
    banned_ids = [await create_profile(ctx, offset=4, role=UserRole.BANNED)]
    blocked_ids = [await create_profile(ctx, offset=5, is_bot_blocked=True)]

    assert await ctx.profile_repo.count() == len(active_ids + admin_ids + banned_ids + blocked_ids)
    assert await ctx.profile_repo.active_count() == len(active_ids + admin_ids)
    assert await ctx.profile_repo.admins_count() == len(admin_ids)
    assert await ctx.profile_repo.banned_count() == len(banned_ids)


async def test_get_active_ids_paginates(repository_context: RepositoryContext):
    ctx = repository_context
    user_ids = [await create_profile(ctx, offset=offset) for offset in (1, 2, 3)]
    await create_profile(ctx, offset=4, role=UserRole.BANNED)
    await create_profile(ctx, offset=5, is_bot_blocked=True)

    first_page = await ctx.profile_repo.get_active_ids(after_id=None, limit=2)
    second_page = await ctx.profile_repo.get_active_ids(after_id=user_ids[1], limit=2)

    assert first_page == user_ids[:2]
    assert second_page == [user_ids[2]]


async def test_bot_user_stats_counts_by_role(repository_context: RepositoryContext):
    ctx = repository_context
    plain_ids = [await create_profile(ctx, offset=1), await create_profile(ctx, offset=2)]
    admin_ids = [await create_profile(ctx, offset=3, role=UserRole.ADMIN)]
    banned_ids = [await create_profile(ctx, offset=4, role=UserRole.BANNED)]
    blocked_ids = [await create_profile(ctx, offset=5, is_bot_blocked=True)]

    stats = await ctx.profile_repo.bot_user_stats()

    assert stats.users_total == len(plain_ids + admin_ids + banned_ids + blocked_ids)
    assert stats.users == len(plain_ids + blocked_ids)
    assert stats.admins == len(admin_ids)
    assert stats.banned == len(banned_ids)
    assert stats.bot_blocked == len(blocked_ids)


async def test_decline_all_suggestions_declines_only_pending(
    repository_context: RepositoryContext,
):
    ctx = repository_context
    author_id = await create_profile(ctx, offset=1)
    other_author_id = await create_profile(ctx, offset=2)

    pending_id = await create_suggestion(ctx, author_id)
    accepted_id = await create_suggestion(ctx, author_id, status=SuggestionStatus.ACCEPTED)
    foreign_id = await create_suggestion(ctx, other_author_id)

    async with ctx.uow.transaction():
        await ctx.profile_repo.decline_all_suggestions(author_id)

    assert (await load_suggestion(ctx, pending_id)).status is SuggestionStatus.DECLINED
    assert (await load_suggestion(ctx, accepted_id)).status is SuggestionStatus.ACCEPTED
    assert (await load_suggestion(ctx, foreign_id)).status is SuggestionStatus.PENDING


async def test_decline_all_suggestions_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
    foreign_bot: MagicMock,
):
    ctx = repository_context
    author_id = await create_profile(ctx, offset=1)
    suggestion_id = await create_suggestion(ctx, author_id)

    async with bot_registry.with_bot(foreign_bot.id), ctx.uow.transaction():
        await ctx.profile_repo.decline_all_suggestions(author_id)

    assert (await load_suggestion(ctx, suggestion_id)).status is SuggestionStatus.PENDING
