from contextvars import Token

from dishka import AsyncContainer
from taskiq.abc.middleware import TaskiqMiddleware
from taskiq.message import TaskiqMessage

from interfaces import BotRegistryProtocol
from usecases.ub_token_resolver import UserBotTokenResolver


class BotContextMiddleware(TaskiqMiddleware):
    def __init__(self, container: AsyncContainer):
        self._container = container
        self._state: dict[int, Token] = {}

    async def pre_execute(self, message: "TaskiqMessage") -> TaskiqMessage:
        bot_id = message.kwargs.get("bot_id")
        if not bot_id:
            return message

        registry = await self._container.get(BotRegistryProtocol)
        resolver = await self._container.get(UserBotTokenResolver)
        token = await resolver.resolve(bot_id)
        if not token:
            return message

        bot = registry.get_or_create(bot_id, token)
        self._state[message.task_id] = registry.set_current(bot)
        return message

    async def post_execute(self, message: "TaskiqMessage", result) -> None:
        await self._reset(message)

    async def on_error(self, message, result, exception) -> None:
        await self._reset(message)

    async def _reset(self, message: "TaskiqMessage"):
        if ctx_token := self._state.pop(message.task_id, None):
            registry = await self._container.get(BotRegistryProtocol)
            registry.reset_current(ctx_token)
