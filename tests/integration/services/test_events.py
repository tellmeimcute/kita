from collections.abc import Callable

import pytest
from aiogram.types import Message
from aiogram.types import User as AiogramUser
from dishka import AsyncContainer

from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus
from events import (
    Event,
    SuggestionAccepted,
    SuggestionDeclined,
    UserProfileCreated,
    UserRegistered,
)
from usecases import ModerateSuggestionUseCase, UserRegisterOrUpdateUseCase

from ..scaffold import BOT_ID, EventRecorder
from .conftest import SuggestionServiceContext, UserTestContext


@pytest.fixture
async def moderate(request_container: AsyncContainer) -> ModerateSuggestionUseCase:
    return await request_container.get(ModerateSuggestionUseCase)


@pytest.fixture
async def pending_suggestion(
    suggestion_context: SuggestionServiceContext,
    make_tg_message: Callable[..., Message],
    event_recorder: EventRecorder,
) -> SuggestionFullDTO:
    async with suggestion_context.uow.transaction():
        created = await suggestion_context.suggestion_service.create(
            suggestion_context.author, [make_tg_message(text="moderate me")]
        )

    event_recorder.reset()

    return created


@pytest.mark.parametrize(
    ("verdict", "event_type"),
    [
        (SuggestionStatus.ACCEPTED, SuggestionAccepted),
        (SuggestionStatus.DECLINED, SuggestionDeclined),
    ],
)
async def test_verdict_publishes_the_event(
    moderate: ModerateSuggestionUseCase,
    event_recorder: EventRecorder,
    pending_suggestion: SuggestionFullDTO,
    verdict: SuggestionStatus,
    event_type: type[Event],
):
    result = await moderate.execute(pending_suggestion.id, verdict)

    assert result.applied is True
    assert event_recorder.events == [
        event_type(bot_id=BOT_ID, suggestion_id=pending_suggestion.id)
    ]


async def test_moderation_publishes_nothing_when_verdict_exists(
    moderate: ModerateSuggestionUseCase,
    event_recorder: EventRecorder,
    pending_suggestion: SuggestionFullDTO,
):
    await moderate.execute(pending_suggestion.id, SuggestionStatus.DECLINED)
    event_recorder.reset()

    result = await moderate.execute(pending_suggestion.id, SuggestionStatus.ACCEPTED)

    assert result.applied is False
    assert event_recorder.events == []


async def test_registration_publishes_user_events_once(
    request_container: AsyncContainer,
    event_recorder: EventRecorder,
    user_test_context: UserTestContext,
    aiogram_user: AiogramUser,
):
    register: UserRegisterOrUpdateUseCase = await request_container.get(
        UserRegisterOrUpdateUseCase
    )

    async with user_test_context.uow.transaction():
        await register.execute(aiogram_user)

    assert event_recorder.events == [
        UserRegistered(bot_id=BOT_ID, user_id=aiogram_user.id),
        UserProfileCreated(bot_id=BOT_ID, user_id=aiogram_user.id),
    ]

    event_recorder.reset()

    async with user_test_context.uow.transaction():
        await register.execute(aiogram_user)

    assert event_recorder.events == []
