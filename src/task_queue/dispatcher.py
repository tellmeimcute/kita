from task_queue.tasks import suggestion_accepted


class SuggestionTaskDispatcher:
    async def accepted(self, bot_id: int, suggestion_id: int) -> None:
        await suggestion_accepted.kiq(bot_id=bot_id, suggestion_id=suggestion_id)
