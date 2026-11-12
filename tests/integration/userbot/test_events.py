from events import UserbotRegistered

from ..scaffold import BOT_ID, CHANNEL_INPUT, EventRecorder
from .conftest import UserBotTestContext


async def test_registration_publishes_the_userbot_event(
    event_recorder: EventRecorder,
    userbot_test_context: UserBotTestContext,
):
    ctx = userbot_test_context

    await ctx.register.execute(ctx.raw_token, CHANNEL_INPUT, owner_id=ctx.owner_id)

    assert event_recorder.events == [
        UserbotRegistered(bot_id=BOT_ID, userbot_id=BOT_ID, owner_id=ctx.owner_id)
    ]
