from database.dto import UserDTO
from database.repository import UserProfileRepository, UserRepository
from services.user import UserService
from services.user_profile import UserProfileService

from ..concurrency import run_in_parallel
from ..readers import load_profile, load_user
from ..scaffold import FakeBotRegistry
from .conftest import UserTestContext

RACE_USER_ID_OFFSET = 9_000


def race_user_dto(ctx: UserTestContext) -> UserDTO:
    return ctx.test_user_dto.model_copy(
        update={
            "user_id": ctx.test_user_dto.user_id + RACE_USER_ID_OFFSET,
            "username": "race_user",
        }
    )


async def test_get_or_create_survives_concurrent_registration(
    user_test_context: UserTestContext,
    bot_registry: FakeBotRegistry,
):
    ctx = user_test_context
    user_dto = race_user_dto(ctx)

    first, second = await run_in_parallel(
        ctx.session_maker,
        service_factory=lambda session: UserService(
            UserRepository(session, bot_registry), bot_registry
        ),
        action=lambda service: service.get_or_create(user_dto),
    )

    for result in (first, second):
        assert not isinstance(result, BaseException), result

    assert second.user_id == user_dto.user_id
    assert await load_user(ctx, user_dto.user_id) is not None


async def test_profile_get_or_create_survives_concurrent_creation(
    user_test_context: UserTestContext,
    bot_registry: FakeBotRegistry,
):
    ctx = user_test_context
    user_dto = race_user_dto(ctx)

    async with ctx.session_maker.begin() as session:
        await UserRepository(session, bot_registry).create(user_dto)

    first, second = await run_in_parallel(
        ctx.session_maker,
        service_factory=lambda session: UserProfileService(
            UserProfileRepository(session, bot_registry), bot_registry
        ),
        action=lambda service: service.get_or_create(user_dto.user_id),
    )

    for result in (first, second):
        assert not isinstance(result, BaseException), result

    assert second.user_id == user_dto.user_id
    assert await load_profile(ctx, user_dto.user_id) is not None
