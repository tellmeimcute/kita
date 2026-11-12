from collections.abc import Callable

import pytest
from aiogram.types import Message
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto import SuggestionFullDTO
from database.enums import SuggestionStatus
from database.repository import UserProfileRepository, UserRepository
from events import (
    Event,
    EventBus,
    SuggestionAccepted,
    SuggestionDeclined,
    UserProfileCreated,
    UserRegistered,
)
from services.user import UserService
from services.user_profile import UserProfileService
from usecases import ModerateSuggestionUseCase, UserRegisterOrUpdateUseCase

from ..concurrency import run_in_parallel
from ..scaffold import BOT_ID, BotStack, EventRecorder
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


async def test_concurrent_first_updates_publish_each_event_once(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    aiogram_user: AiogramUser,
    bots: BotStack,
):
    i18n: I18n = await request_container.get(I18n)
    recorders: list[EventRecorder] = []

    def usecase_factory(session: AsyncSession) -> UserRegisterOrUpdateUseCase:
        recorder = EventRecorder()
        recorders.append(recorder)

        return UserRegisterOrUpdateUseCase(
            bot_context=bots.context,
            i18n=i18n,
            user_service=UserService(UserRepository(session, bots.context), bots.context),
            profile_service=UserProfileService(
                UserProfileRepository(session, bots.context), bots.context
            ),
            events=EventBus(recorder.listeners()),
        )

    first, second = await run_in_parallel(
        user_test_context.session_maker,
        service_factory=usecase_factory,
        action=lambda usecase: usecase.execute(aiogram_user),
    )

    for result in (first, second):
        assert not isinstance(result, BaseException), result

    published = [event for recorder in recorders for event in recorder.events]

    assert published.count(UserRegistered(bot_id=BOT_ID, user_id=aiogram_user.id)) == 1
    assert published.count(UserProfileCreated(bot_id=BOT_ID, user_id=aiogram_user.id)) == 1
    assert len(published) == 2
