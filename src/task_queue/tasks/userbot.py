from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from database.enums import UserRole
from interfaces import BotRegistryProtocol, UnitOfWorkProtocol, UserProfileServiceProtocol
from services import WebhookService
from task_queue.broker import broker
from usecases.ub_token_resolver import UserBotTokenResolver


@broker.task
@inject(patch_module=True)
async def new_userbot(
    bot_id: int,
    userbot_id: int,
    owner_id: int,
    bot_registry: FromDishka[BotRegistryProtocol],
    uow: FromDishka[UnitOfWorkProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    webhook_service: FromDishka[WebhookService],
    token_resolver: FromDishka[UserBotTokenResolver],
):
    userbot_token = await token_resolver.resolve(userbot_id)
    async with uow.transaction(), bot_registry.with_bot(userbot_id, userbot_token):
        await profile_service.get_or_create(owner_id)
        await profile_service.update(owner_id, role=UserRole.ADMIN)
    await webhook_service.set_webhook(bot_registry.get(userbot_id))

    logger.info("New userbot {} registered, admin {}", userbot_id, owner_id)
