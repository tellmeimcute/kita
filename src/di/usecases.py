
from dishka import Provider, Scope, provide
from usecases.moderate_suggestion import ModerateSuggestionUseCase

class UsecasesProvider(Provider):
    moderate_suggestion = provide(ModerateSuggestionUseCase, scope=Scope.REQUEST)
