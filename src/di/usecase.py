from dishka import Provider, Scope, provide

from usecases import (
    BanUserUseCase,
    BroadcastUseCase,
    DemoteUserUseCase,
    MessageUserUseCase,
    ModerateSuggestionUseCase,
    PromoteUserUseCase,
    UserbotActiveToggleUseCase,
    UserbotDemoteAdminsUseCase,
    UserBotRegisterUseCase,
    UserbotSelectUseCase,
    UserbotUpdateChannelUseCase,
    UserbotUpdateTokenUseCase,
    UserRegisterOrUpdateUseCase,
)


class UseCaseProvider(Provider):
    scope = Scope.REQUEST

    moderate_suggestion = provide(ModerateSuggestionUseCase)
    ban_user = provide(BanUserUseCase)
    promote_user = provide(PromoteUserUseCase)
    demote_user = provide(DemoteUserUseCase)
    broadcast = provide(BroadcastUseCase)
    message_user = provide(MessageUserUseCase)
    register_or_update_user = provide(UserRegisterOrUpdateUseCase)
    ub_register = provide(UserBotRegisterUseCase)
    ub_select = provide(UserbotSelectUseCase)
    ub_active_toggle = provide(UserbotActiveToggleUseCase)
    ub_update_token = provide(UserbotUpdateTokenUseCase)
    ub_update_channel = provide(UserbotUpdateChannelUseCase)
    ub_demote_admins = provide(UserbotDemoteAdminsUseCase)
