from core.enums import RenderType
from core.schemas import MediaInfo
from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus

from ..readers import count_media, load_suggestion
from ..scaffold import BOT_ID, FakeBotRegistry
from .conftest import RepositoryContext


async def create_suggestion(
    ctx: RepositoryContext,
    *,
    media: list[MediaInfo] | None = None,
    caption: str | None = "caption",
    anonymous: bool = False,
    media_group_id: str | None = None,
    forwarded_from: str | None = None,
) -> SuggestionFullDTO:
    async with ctx.uow.transaction():
        return await ctx.suggestion_repo.create(
            author_id=ctx.test_user_dto.user_id,
            anonymous=anonymous,
            mediainfo=[MediaInfo("photo", "photo-1")] if media is None else media,
            caption=caption,
            media_group_id=media_group_id,
            forwarded_from=forwarded_from,
        )


async def test_create_persists_suggestion_with_media(repository_context: RepositoryContext):
    ctx = repository_context

    created = await create_suggestion(
        ctx,
        media=[MediaInfo("photo", "photo-1"), MediaInfo("video", "video-1")],
        caption="hello",
        media_group_id="album-1",
        forwarded_from="Source Channel",
    )

    assert created.caption == "hello"
    assert created.author_id == ctx.test_user_dto.user_id
    assert created.status is SuggestionStatus.PENDING
    assert created.media_group_id == "album-1"
    assert created.forwarded_from == "Source Channel"
    assert created.render_type is RenderType.MEDIAGROUP
    assert [(media.filetype, media.telegram_file_id) for media in created.media] == [
        ("photo", "photo-1"),
        ("video", "video-1"),
    ]

    row = await load_suggestion(ctx, created.id)

    assert row.bot_id == BOT_ID
    assert await count_media(ctx, created.id) == len(created.media)


async def test_get_by_id_returns_author_and_media(repository_context: RepositoryContext):
    ctx = repository_context

    created = await create_suggestion(ctx, caption="hello")

    async with ctx.uow.transaction():
        found = await ctx.suggestion_repo.get_by_id(created.id)

    assert isinstance(found, SuggestionFullDTO)
    assert found.id == created.id
    assert found.caption == "hello"
    assert found.author.user_id == ctx.test_user_dto.user_id
    assert found.author.username == ctx.test_user_dto.username
    assert [media.filetype for media in found.media] == ["photo"]


async def test_get_by_id_returns_none_for_unknown_id(repository_context: RepositoryContext):
    ctx = repository_context

    async with ctx.uow.transaction():
        assert await ctx.suggestion_repo.get_by_id(999_999) is None


async def test_get_by_id_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
):
    ctx = repository_context

    created = await create_suggestion(ctx)

    bot_registry.bot.id = BOT_ID + 1

    async with ctx.uow.transaction():
        assert await ctx.suggestion_repo.get_by_id(created.id) is None


async def test_update_persists_changes(repository_context: RepositoryContext):
    ctx = repository_context

    created = await create_suggestion(ctx)

    async with ctx.uow.transaction():
        await ctx.suggestion_repo.update(
            created.id,
            status=SuggestionStatus.ACCEPTED,
            caption="edited",
        )

    row = await load_suggestion(ctx, created.id)

    assert row.status is SuggestionStatus.ACCEPTED
    assert row.caption == "edited"


async def test_update_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
):
    ctx = repository_context

    created = await create_suggestion(ctx, caption="intact")

    bot_registry.bot.id = BOT_ID + 1

    async with ctx.uow.transaction():
        await ctx.suggestion_repo.update(created.id, caption="hacked")

    bot_registry.bot.id = BOT_ID

    row = await load_suggestion(ctx, created.id)

    assert row.caption == "intact"


async def test_save_applies_changed_fields(repository_context: RepositoryContext):
    ctx = repository_context

    created = await create_suggestion(ctx)

    async with ctx.uow.transaction():
        dto = await ctx.suggestion_repo.get_by_id(created.id)
        dto.status = SuggestionStatus.DECLINED
        dto.caption = "changed"
        await ctx.suggestion_repo.save(dto)

    row = await load_suggestion(ctx, created.id)

    assert row.status is SuggestionStatus.DECLINED
    assert row.caption == "changed"


async def test_save_of_untouched_dto_keeps_row_as_is(repository_context: RepositoryContext):
    ctx = repository_context

    created = await create_suggestion(ctx, caption="original")

    async with ctx.uow.transaction():
        dto = await ctx.suggestion_repo.get_by_id(created.id)
        await ctx.suggestion_repo.save(dto)

    row = await load_suggestion(ctx, created.id)

    assert row.caption == "original"
    assert row.status is SuggestionStatus.PENDING


async def test_get_active_returns_only_pending_in_id_order(repository_context: RepositoryContext):
    ctx = repository_context

    first = await create_suggestion(ctx, caption="first")
    second = await create_suggestion(ctx, caption="second")
    third = await create_suggestion(ctx, caption="third")

    async with ctx.uow.transaction():
        await ctx.suggestion_repo.update(second.id, status=SuggestionStatus.ACCEPTED)

    async with ctx.uow.transaction():
        active = await ctx.suggestion_repo.get_active()

    assert [suggestion.id for suggestion in active] == [first.id, third.id]
    assert [suggestion.caption for suggestion in active] == ["first", "third"]
    assert active[0].author.user_id == ctx.test_user_dto.user_id


async def test_get_active_respects_limit_and_offset(repository_context: RepositoryContext):
    ctx = repository_context

    suggestions = [await create_suggestion(ctx, caption=f"s{index}") for index in range(3)]

    async with ctx.uow.transaction():
        page = await ctx.suggestion_repo.get_active(limit=1, offset=1)

    assert [suggestion.id for suggestion in page] == [suggestions[1].id]


async def test_get_active_ignores_foreign_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
):
    ctx = repository_context

    await create_suggestion(ctx)

    bot_registry.bot.id = BOT_ID + 1

    async with ctx.uow.transaction():
        assert await ctx.suggestion_repo.get_active() == []


async def test_user_stats_counts_by_status(repository_context: RepositoryContext):
    ctx = repository_context

    accepted = await create_suggestion(ctx, caption="accepted")
    declined = await create_suggestion(ctx, caption="declined")
    await create_suggestion(ctx, caption="pending")

    async with ctx.uow.transaction():
        await ctx.suggestion_repo.update(accepted.id, status=SuggestionStatus.ACCEPTED)
        await ctx.suggestion_repo.update(declined.id, status=SuggestionStatus.DECLINED)

    async with ctx.uow.transaction():
        stats = await ctx.suggestion_repo.user_stats(ctx.test_user_dto.user_id)

    assert (stats.total, stats.accepted, stats.declined) == (3, 1, 1)


async def test_user_stats_are_zero_for_user_without_suggestions(
    repository_context: RepositoryContext,
):
    ctx = repository_context

    async with ctx.uow.transaction():
        stats = await ctx.suggestion_repo.user_stats(999_999)

    assert (stats.total, stats.accepted, stats.declined) == (0, 0, 0)


async def test_count_counts_only_current_bot(
    repository_context: RepositoryContext,
    bot_registry: FakeBotRegistry,
):
    ctx = repository_context

    created = [await create_suggestion(ctx) for _ in range(2)]

    async with ctx.uow.transaction():
        assert await ctx.suggestion_repo.count() == len(created)

    bot_registry.bot.id = BOT_ID + 1

    async with ctx.uow.transaction():
        assert await ctx.suggestion_repo.count() == 0
