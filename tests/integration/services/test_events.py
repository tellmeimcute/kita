from collections.abc import Callable

import pytest
from aiogram.types import Message
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from database.dto import SuggestionFullDTO, UserDTO
from database.enums import SuggestionStatus, UserRole
from database.repository import UserProfileRepository, UserRepository
from events import (
    Event,
    EventBus,
    ListenerRegistry,
    SuggestionAccepted,
    SuggestionDeclined,
    UserBanned,
    UserProfileCreated,
    UserRegistered,
)
from interfaces import EventBusProtocol
from services.user import UserService
from services.user_profile import UserProfileService
from usecases import (
    ChangeRoleUseCase,
    ModerateSuggestionUseCase,
    UserRegisterOrUpdateUseCase,
)

from ..concurrency import run_in_parallel
from ..scaffold import (
    BOT_ID,
    BotStack,
    EventRecorder,
    NoListenerResolver,
    make_userbot_dto,
)
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
            events=EventBus(ListenerRegistry(recorder.listeners()), NoListenerResolver()),
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


@pytest.fixture
async def change_role(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    bots: BotStack,
) -> ChangeRoleUseCase:
    return ChangeRoleUseCase(
        user_service=user_test_context.user_service,
        user_profile_service=user_test_context.profile_service,
        userbot=make_userbot_dto(owner_id=user_test_context.test_user_dto.user_id),
        events=await request_container.get(EventBusProtocol),
    )


async def test_ban_publishes_the_user_banned_event(
    change_role: ChangeRoleUseCase,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = user_dto_factory()

    async with user_test_context.uow.transaction():
        await user_test_context.user_service.get_or_create(target)

    async with user_test_context.uow.transaction():
        banned = await change_role.execute(target.user_id, UserRole.BANNED, caller=admin)

    assert banned.role is UserRole.BANNED
    assert event_recorder.events == [
        UserBanned(bot_id=BOT_ID, user_id=target.user_id, admin_id=admin.user_id)
    ]


async def test_role_change_that_is_not_a_ban_publishes_nothing(
    change_role: ChangeRoleUseCase,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = user_dto_factory()

    async with user_test_context.uow.transaction():
        await user_test_context.user_service.get_or_create(target)

    async with user_test_context.uow.transaction():
        promoted = await change_role.execute(target.user_id, UserRole.ADMIN, caller=admin)

    assert promoted.role is UserRole.ADMIN
    assert event_recorder.events == []
