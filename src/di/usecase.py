from dishka import Provider, Scope, provide

from usecases import (
    BroadcastUseCase,
    ChangeRoleUseCase,
    MessageUserUseCase,
    ModerateSuggestionUseCase,
    UserbotActiveToggleUseCase,
    UserbotDemoteAdminsUseCase,
    UserBotRegisterUseCase,
    UserbotUpdateChannelUseCase,
    UserbotUpdateTokenUseCase,
    UserRegisterOrUpdateUseCase,
)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    moderate_suggestion = provide(ModerateSuggestionUseCase)
    change_role = provide(ChangeRoleUseCase)
    broadcast = provide(BroadcastUseCase)
    message_user = provide(MessageUserUseCase)
    register_or_update_user = provide(UserRegisterOrUpdateUseCase)
    ub_register = provide(UserBotRegisterUseCase)
    ub_active_toggle = provide(UserbotActiveToggleUseCase)
    ub_update_token = provide(UserbotUpdateTokenUseCase)
    ub_update_channel = provide(UserbotUpdateChannelUseCase)
    ub_demote_admins = provide(UserbotDemoteAdminsUseCase)
