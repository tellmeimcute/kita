from database.dto import UserDTO
from database.repository import UserProfileRepository, UserRepository
from services.user import UserService
from services.user_profile import UserProfileService

from ..concurrency import run_in_parallel
from ..readers import load_profile, load_user
from ..scaffold import BotStack
from .conftest import UserTestContext

RACE_USER_ID_OFFSET = 9_000


def race_user_dto(ctx: UserTestContext) -> UserDTO:
    return ctx.test_user_dto.model_copy(
        update={
            "user_id": ctx.test_user_dto.user_id + RACE_USER_ID_OFFSET,
            "username": "race_user",
        }
    )


def assert_only_one_created(results: list) -> None:
    created_flags = []
    for result in results:
        assert not isinstance(result, BaseException), result
        created_flags.append(result.created)

    assert created_flags.count(True) == 1


async def test_get_or_create_survives_concurrent_registration(
    user_test_context: UserTestContext,
    bots: BotStack,
):
    ctx = user_test_context
    user_dto = race_user_dto(ctx)

    first, second = await run_in_parallel(
        ctx.session_maker,
        service_factory=lambda session: UserService(
            UserRepository(session, bots.context), bots.context
        ),
        action=lambda service: service.get_or_create(user_dto),
    )

    assert_only_one_created([first, second])
    assert second.dto.user_id == user_dto.user_id
    assert await load_user(ctx, user_dto.user_id) is not None


async def test_profile_get_or_create_survives_concurrent_creation(
    user_test_context: UserTestContext,
    bots: BotStack,
):
    ctx = user_test_context
    user_dto = race_user_dto(ctx)

    async with ctx.session_maker.begin() as session:
        await UserRepository(session, bots.context).create(user_dto)

    first, second = await run_in_parallel(
        ctx.session_maker,
        service_factory=lambda session: UserProfileService(
            UserProfileRepository(session, bots.context), bots.context
        ),
        action=lambda service: service.get_or_create(user_dto.user_id),
    )

    assert_only_one_created([first, second])
    assert second.dto.user_id == user_dto.user_id
    assert await load_profile(ctx, user_dto.user_id) is not None
