from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from database.enums import UserRole
from interfaces import (
    BotResolverProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
    WebhookServiceProtocol,
)
from task_queue.broker import get_broker
from usecases.ub_token_resolver import UserBotTokenResolver

broker = get_broker()


@broker.task
@inject(patch_module=True)
async def new_userbot(
    bot_id: int,
    userbot_id: int,
    owner_id: int,
    allowed_updates: list[str],
    bot_resolver: FromDishka[BotResolverProtocol],
    uow: FromDishka[UnitOfWorkProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    webhook_service: FromDishka[WebhookServiceProtocol],
    token_resolver: FromDishka[UserBotTokenResolver],
):
    userbot_token = await token_resolver.resolve(userbot_id)
    bot = bot_resolver.get_or_create(userbot_id, userbot_token)

    async with uow.transaction(), bot_resolver.with_bot(bot):
        await profile_service.get_or_create(owner_id)
        await profile_service.update(owner_id, role=UserRole.ADMIN)
    await webhook_service.set_webhook(bot, allowed_updates=allowed_updates)

    logger.info("New userbot {} registered, admin {}", userbot_id, owner_id)
