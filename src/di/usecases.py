
from dishka import Provider, Scope, provide

from usecases.moderate_suggestion import ModerateSuggestionUseCase
from usecases.change_role import ChangeRoleUseCase

class UsecasesProvider(Provider):
    moderate_suggestion = provide(ModerateSuggestionUseCase, scope=Scope.REQUEST)
    change_role = provide(ChangeRoleUseCase, scope=Scope.REQUEST)
