
from dishka import Provider, Scope, provide

from usecases.broadcast import BroadcastUseCase
from usecases.change_role import ChangeRoleUseCase
from usecases.moderate_suggestion import ModerateSuggestionUseCase


class UsecasesProvider(Provider):
    moderate_suggestion = provide(ModerateSuggestionUseCase, scope=Scope.REQUEST)
    change_role = provide(ChangeRoleUseCase, scope=Scope.REQUEST)
    broadcast = provide(BroadcastUseCase, scope=Scope.REQUEST)
