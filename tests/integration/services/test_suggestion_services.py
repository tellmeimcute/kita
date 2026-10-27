from collections.abc import Callable

import pytest
from aiogram.types import Message

from core.consts import SUGGESTION_CAPTION_LIMIT, SUGGESTION_TEXT_LIMIT
from core.enums import RenderType
from core.exceptions import UnsupportedPayload
from core.schemas import UserStats
from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus

from ..readers import count_media, count_suggestions, load_suggestion
from .conftest import SuggestionServiceContext


async def create_suggestion(
    ctx: SuggestionServiceContext,
    *messages,
    anonymous: bool = False,
) -> SuggestionFullDTO:
    async with ctx.uow.transaction():
        return await ctx.suggestion_service.create(ctx.author, list(messages), anonymous=anonymous)


async def test_create_from_text_message(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    created = await create_suggestion(ctx, make_tg_message(text="hello"))

    assert created.caption == "hello"
    assert created.media == []
    assert created.render_type is RenderType.MESSAGE
    assert created.author.user_id == ctx.author.user_id

    row = await load_suggestion(ctx, created.id)
    assert row.caption == "hello"
    assert row.anonymous is False


async def test_create_from_album_keeps_every_media(
    suggestion_context: SuggestionServiceContext,
    make_tg_album: Callable[..., list[Message]],
):
    ctx = suggestion_context

    created = await create_suggestion(ctx, *make_tg_album(3, caption="album caption"))

    assert created.caption == "album caption"
    assert created.media_group_id == "album"
    assert created.render_type is RenderType.MEDIAGROUP
    assert [media.telegram_file_id for media in created.media] == [
        "photo-0",
        "photo-1",
        "photo-2",
    ]

    assert await count_media(ctx, created.id) == len(created.media)


@pytest.mark.parametrize(
    ("media_kwargs", "expected"),
    [
        ({"photo": "photo-id"}, ("photo", "photo-id")),
        ({"video": "video-id"}, ("video", "video-id")),
        ({"document": "document-id"}, ("document", "document-id")),
        ({"animation": "animation-id"}, ("document", "animation-id")),
    ],
)
async def test_create_maps_media_type(
    suggestion_context: SuggestionServiceContext,
    media_kwargs: dict,
    expected: tuple[str, str],
    make_tg_message: Callable[..., Message],
):
    created = await create_suggestion(suggestion_context, make_tg_message(**media_kwargs))

    assert [(media.filetype, media.telegram_file_id) for media in created.media] == [expected]


async def test_create_stores_forwarded_from(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    message = make_tg_message(text="look at this", forwarded_from="Source Channel")

    created = await create_suggestion(suggestion_context, message)

    assert created.forwarded_from == "Source Channel"


async def test_create_stores_anonymous_flag(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    created = await create_suggestion(ctx, make_tg_message(text="hidden author"), anonymous=True)

    assert created.anonymous is True
    assert (await load_suggestion(ctx, created.id)).anonymous is True


async def test_create_rejects_empty_payload(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    with pytest.raises(UnsupportedPayload):
        await create_suggestion(ctx, make_tg_message())

    assert await count_suggestions(ctx) == 0


async def test_create_rejects_too_long_caption_with_media(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context
    message = make_tg_message(caption="x" * (SUGGESTION_CAPTION_LIMIT + 1), photo="photo-id")

    with pytest.raises(UnsupportedPayload):
        await create_suggestion(ctx, message)

    assert await count_suggestions(ctx) == 0


async def test_create_rejects_too_long_text(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context
    message = make_tg_message(text="x" * (SUGGESTION_TEXT_LIMIT + 1))

    with pytest.raises(UnsupportedPayload):
        await create_suggestion(ctx, message)

    assert await count_suggestions(ctx) == 0


async def test_get_returns_created_suggestion(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context
    created = await create_suggestion(ctx, make_tg_message(text="read me"))

    async with ctx.uow.transaction():
        found = await ctx.suggestion_service.get(created.id)

    assert found.id == created.id
    assert found.caption == "read me"
    assert found.author.user_id == ctx.author.user_id


async def test_get_active_excludes_moderated(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    pending = await create_suggestion(ctx, make_tg_message(text="pending"))
    accepted = await create_suggestion(ctx, make_tg_message(text="accepted"))

    async with ctx.uow.transaction():
        await ctx.suggestion_service.update_by_id(accepted.id, status=SuggestionStatus.ACCEPTED)

    async with ctx.uow.transaction():
        active = await ctx.suggestion_service.get_active()

    assert [suggestion.id for suggestion in active] == [pending.id]


async def test_update_persists_status_change(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context
    created = await create_suggestion(ctx, make_tg_message(text="moderate me"))

    async with ctx.uow.transaction():
        created.status = SuggestionStatus.ACCEPTED
        await ctx.suggestion_service.update(created)

    row = await load_suggestion(ctx, created.id)

    assert row.status is SuggestionStatus.ACCEPTED


async def test_user_stats_are_zero_without_suggestions(
    suggestion_context: SuggestionServiceContext,
):
    ctx = suggestion_context

    async with ctx.uow.transaction():
        stats = await ctx.suggestion_service.get_user_stats(ctx.author)

    assert stats == UserStats(total=0, accepted=0, declined=0)


async def test_user_stats_counts_by_status(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    accepted = await create_suggestion(ctx, make_tg_message(text="accepted"))
    declined = await create_suggestion(ctx, make_tg_message(text="declined"))
    await create_suggestion(ctx, make_tg_message(text="pending"))

    async with ctx.uow.transaction():
        await ctx.suggestion_service.update_by_id(accepted.id, status=SuggestionStatus.ACCEPTED)
        await ctx.suggestion_service.update_by_id(declined.id, status=SuggestionStatus.DECLINED)

    async with ctx.uow.transaction():
        stats = await ctx.suggestion_service.get_user_stats(ctx.author)

    assert (stats.total, stats.accepted, stats.declined) == (3, 1, 1)


async def test_user_stats_cached_after_commit(suggestion_context: SuggestionServiceContext):
    ctx = suggestion_context

    async with ctx.uow.transaction():
        await ctx.suggestion_service.get_user_stats(ctx.author)

    assert await ctx.stats_redis.get(ctx.stats_key) == UserStats(total=0, accepted=0, declined=0)


async def test_user_stats_not_cached_when_transaction_rolled_back(
    suggestion_context: SuggestionServiceContext,
):
    ctx = suggestion_context

    async with ctx.uow.transaction():
        await ctx.suggestion_service.get_user_stats(ctx.author)
        await ctx.uow.rollback()

    assert await ctx.stats_redis.get(ctx.stats_key) is None


async def test_user_stats_cache_invalidated_on_create(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
):
    ctx = suggestion_context

    async with ctx.uow.transaction():
        await ctx.suggestion_service.get_user_stats(ctx.author)

    assert await ctx.stats_redis.get(ctx.stats_key) is not None

    await create_suggestion(ctx, make_tg_message(text="new suggestion"))

    assert await ctx.stats_redis.get(ctx.stats_key) is None

    async with ctx.uow.transaction():
        stats = await ctx.suggestion_service.get_user_stats(ctx.author)

    assert stats.total == 1
