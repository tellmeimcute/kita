import asyncio
from collections.abc import Sequence
from itertools import batched

from aiogram.utils.i18n import I18n
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger
from taskiq import AsyncTaskiqTask, TaskiqResult

from interfaces import NotifierServiceProtocol, UnitOfWorkProtocol, UserServiceProtocol
from task_queue.broker import broker
from usecases import BroadcastUseCase
from usecases.broadcast import BatchResult

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
    broadcast_usecase: FromDishka[BroadcastUseCase],
) -> BatchResult:
    return await broadcast_usecase.execute_batch(
        user_ids=user_ids,
        source_chat_id=source_chat_id,
        source_message_ids=source_message_ids,
        is_forwarded=is_forwarded,
    )


@broker.task
@inject(patch_module=True)
async def broadcast(
    bot_id: int,
    caller_id: int,
    source_chat_id: int,
    source_message_ids: Sequence[int],
    is_forwarded: bool,
    uow: FromDishka[UnitOfWorkProtocol],
    user_service: FromDishka[UserServiceProtocol],
    broadcast_usecase: FromDishka[BroadcastUseCase],
    i18n: FromDishka[I18n],
    notifier: FromDishka[NotifierServiceProtocol],
):
    total = 0
    users_ok = 0

    try:
        total = await uow.profiles.active_count()

        tasks: list[AsyncTaskiqTask] = []
        cursor = None
        while ids := await uow.profiles.get_active_ids(cursor, PAGE_SIZE):
            cursor = ids[-1]
            for chunk in batched(ids, CHUNK_SIZE):  # noqa B911
                task: AsyncTaskiqTask = await send_batch.kiq(
                    bot_id=bot_id,
                    user_ids=chunk,
                    source_chat_id=source_chat_id,
                    source_message_ids=source_message_ids,
                    is_forwarded=is_forwarded,
                )
                tasks.append(task)
                await asyncio.sleep(1.0)

        results = await asyncio.gather(
            *[r.wait_result(check_interval=1.0, timeout=300) for r in tasks],
            return_exceptions=True,
        )
        users_ok = sum(
            r.return_value.delivered
            for r in results
            if isinstance(r, TaskiqResult) and not r.is_err
        )
    finally:
        await broadcast_usecase.unlock()
        logger.info(
            "Broadcast bot_id {} caller_id {} complete. Total {}, success {}",
            bot_id,
            caller_id,
            total,
            users_ok,
        )

    caller = await user_service.get(caller_id)
    with i18n.context(), i18n.use_locale(caller.language_code):
        i18n_kwargs = {
            "total": total,
            "delivered": users_ok,
            "failure": total - users_ok,
        }
        await notifier.send_text(caller, "broadcast_completed", i18n_kwargs)
