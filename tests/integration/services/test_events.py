from collections.abc import Callable

import pytest
from aiogram.types import Message
from aiogram.types import User as AiogramUser
from aiogram.utils.i18n import I18n
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import UserImmuneError
from core.schemas import MediaInfo
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
from interfaces import (
    EventBusProtocol,
    SuggestionRepositoryProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
)
from services.user import UserService
from services.user_profile import UserProfileService
from usecases import (
    BanUserUseCase,
    DemoteUserUseCase,
    ModerateSuggestionUseCase,
    PromoteUserUseCase,
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
async def promote(
    user_test_context: UserTestContext,
) -> PromoteUserUseCase:
    return PromoteUserUseCase(
        uow=user_test_context.uow,
        user_profile_service=user_test_context.profile_service,
        userbot=make_userbot_dto(owner_id=user_test_context.test_user_dto.user_id),
    )


@pytest.fixture
async def demote(
    user_test_context: UserTestContext,
) -> DemoteUserUseCase:
    return DemoteUserUseCase(
        uow=user_test_context.uow,
        user_profile_service=user_test_context.profile_service,
        userbot=make_userbot_dto(owner_id=user_test_context.test_user_dto.user_id),
    )


@pytest.fixture
async def ban_user(
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    bots: BotStack,
) -> BanUserUseCase:
    return BanUserUseCase(
        uow=user_test_context.uow,
        user_profile_service=user_test_context.profile_service,
        suggestion_service=await request_container.get(SuggestionServiceProtocol),
        userbot=make_userbot_dto(owner_id=user_test_context.test_user_dto.user_id),
        events=await request_container.get(EventBusProtocol),
    )


async def create_target(
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
) -> UserDTO:
    target = user_dto_factory()

    async with user_test_context.uow.transaction():
        await user_test_context.user_service.get_or_create(target)

    return target


async def create_suggestion_of(
    request_container: AsyncContainer,
    author_id: int,
    *,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> int:
    repo = await request_container.get(SuggestionRepositoryProtocol)
    uow = await request_container.get(UnitOfWorkProtocol)

    async with uow.transaction():
        created = await repo.create(
            author_id=author_id,
            anonymous=False,
            mediainfo=[MediaInfo("photo", "photo-1")],
            caption="caption",
            media_group_id=None,
            forwarded_from=None,
        )
        if status is not SuggestionStatus.PENDING:
            await repo.update(created.id, status=status)

    return created.id


async def test_ban_declines_the_pending_suggestions_and_publishes_the_ban(
    ban_user: BanUserUseCase,
    request_container: AsyncContainer,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = await create_target(user_test_context, user_dto_factory)

    pending_id = await create_suggestion_of(request_container, target.user_id)
    accepted_id = await create_suggestion_of(
        request_container,
        target.user_id,
        status=SuggestionStatus.ACCEPTED,
    )

    banned = await ban_user.execute(target.user_id, caller=admin)

    assert banned.role is UserRole.BANNED
    suggestions = await request_container.get(SuggestionServiceProtocol)
    assert (await suggestions.get(pending_id)).status is SuggestionStatus.DECLINED
    assert (await suggestions.get(accepted_id)).status is SuggestionStatus.ACCEPTED

    assert event_recorder.events == [
        SuggestionDeclined(bot_id=BOT_ID, suggestion_id=pending_id),
        UserBanned(bot_id=BOT_ID, user_id=target.user_id, admin_id=admin.user_id),
    ]


async def test_ban_without_suggestions_publishes_only_the_ban(
    ban_user: BanUserUseCase,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = await create_target(user_test_context, user_dto_factory)

    banned = await ban_user.execute(target.user_id, caller=admin)

    assert banned.role is UserRole.BANNED
    assert event_recorder.events == [
        UserBanned(bot_id=BOT_ID, user_id=target.user_id, admin_id=admin.user_id)
    ]


async def test_ban_refuses_an_immune_user(
    ban_user: BanUserUseCase,
    user_test_context: UserTestContext,
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto

    with pytest.raises(UserImmuneError):
        await ban_user.execute(admin.user_id, caller=admin)

    assert event_recorder.events == []


async def test_promote_makes_an_admin_and_publishes_nothing(
    promote: PromoteUserUseCase,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = await create_target(user_test_context, user_dto_factory)

    promoted = await promote.execute(target.user_id, caller=admin)

    assert promoted.role is UserRole.ADMIN
    assert event_recorder.events == []


async def test_demote_returns_the_user_to_the_plain_role(
    promote: PromoteUserUseCase,
    demote: DemoteUserUseCase,
    user_test_context: UserTestContext,
    user_dto_factory: Callable[..., UserDTO],
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto
    target = await create_target(user_test_context, user_dto_factory)

    await promote.execute(target.user_id, caller=admin)
    demoted = await demote.execute(target.user_id, caller=admin)

    assert demoted.role is UserRole.USER
    assert event_recorder.events == []


async def test_promote_refuses_an_immune_user(
    promote: PromoteUserUseCase,
    user_test_context: UserTestContext,
    event_recorder: EventRecorder,
):
    admin = user_test_context.test_user_dto

    with pytest.raises(UserImmuneError):
        await promote.execute(admin.user_id, caller=admin)

    assert event_recorder.events == []
