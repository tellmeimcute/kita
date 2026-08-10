import asyncio
from collections.abc import Sequence
from itertools import batched

from aiogram.utils.i18n import I18n
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from interfaces import (
    NotifierServiceProtocol,
    UnitOfWorkProtocol,
    UserProfileServiceProtocol,
)
from task_queue.broker import broker

PAGE_SIZE = 20
CHUNK_SIZE = 5


@broker.task
@inject(patch_module=True)
async def send_batch(
    bot_id: int,
    user_ids: Sequence[int],
    source_chat_id: int,
    source_message_ids: Sequence[int],
    is_forwarded: bool,
    profile_service: FromDishka[UserProfileServiceProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
    i18n: FromDishka[I18n],
):
    send_func = notifier.forward_messages if is_forwarded else notifier.copy_messages

    for user_id in user_ids:
        user_profile = await profile_service.get(user_id)
        with i18n.context(), i18n.use_locale("ru"):
            await send_func(user_profile, source_message_ids, source_chat_id)


@broker.task
@inject(patch_module=True)
async def broadcast(
    bot_id: int,
    source_chat_id: int,
    source_message_ids: Sequence[int],
    is_forwarded: bool,
    uow: FromDishka[UnitOfWorkProtocol],
):
    cursor = None
    while ids := await uow.profiles.get_active_ids(cursor, PAGE_SIZE):
        cursor = ids[-1]
        for chunk in batched(ids, CHUNK_SIZE):  # noqa B911
            await send_batch.kiq(
                bot_id=bot_id,
                user_ids=chunk,
                source_chat_id=source_chat_id,
                source_message_ids=source_message_ids,
                is_forwarded=is_forwarded,
            )
            await asyncio.sleep(1)

    logger.info("Broadcast complete")
