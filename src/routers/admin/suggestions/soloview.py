
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from dishka import FromDishka

from core.exceptions import UserImmuneError
from core.filters import I18nTextFilter, TextArgsFilter
from core.schemas import IDCommand
from core.schemas.viewer import SuggestionViewerData
from database.dto import UserDTO
from database.enums import SuggestionStatus, UserRole
from interfaces import (
    NotifierServiceProtocol,
    SuggestionServiceProtocol,
    UnitOfWorkProtocol,
)
from ui.keyboards import ReplyKeyboard
from ui.state_groups import SuggestionViewerSG
from usecases.change_role import ChangeRoleUseCase
from usecases.moderate_suggestion import ModerateSuggestionUseCase

router = Router(name="admin_suggesions_soloview")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def enter_soloview(
    message: Message,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
    state: FSMContext,
    command: IDCommand,
):
    suggestion_dto = await suggestion_service.get(command.target_id)
    if not suggestion_dto:
        return await notifier.send_text(
            user_dto, "suggestion_not_found",
            i18n_kwargs=dict(suggestion_id=command.target_id)
        )
    
    await state.set_state(SuggestionViewerSG.in_solo_view)
    viewer_data.suggestion_dto = suggestion_dto
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})

    await notifier.send_suggestion(user_dto, suggestion_dto)
    await notifier.send_text(
        user_dto, "wait_verdict_text",
        kb=ReplyKeyboard.viewer_admin_action(),
    )


@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("viewer_accept", verdict=SuggestionStatus.ACCEPTED))
@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("viewer_decline", verdict=SuggestionStatus.DECLINED))
async def soloview_verdict(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    uow: FromDishka[UnitOfWorkProtocol],
    viewer_data: FromDishka[SuggestionViewerData],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    notifier: FromDishka[NotifierServiceProtocol],
    verdict: SuggestionStatus,
):
    suggestion_dto = viewer_data.suggestion_dto
    async with uow.transaction():
        await moderation_usecase.execute(suggestion_dto, verdict, force_update=True)

    await notifier.send_text(
        user_dto, "verdict_rewrite",
        kb=ReplyKeyboardRemove(),
    )
    await state.clear()


@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("ban_btn"))
async def soloview_ban_author(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
    change_role_usecase: FromDishka[ChangeRoleUseCase],
):
    target_id = viewer_data.suggestion_dto.author_id
    target_role = UserRole.BANNED

    try:
        async with uow.transaction():
            await change_role_usecase.execute(
                target_id, target_role, caller=user_dto
            )
    except UserImmuneError:
        return await notifier.send_text(user_dto, "error_user_immune")

    await state.clear()
    await notifier.send_text(
        user_dto, "verdict_rewrite",
        kb=ReplyKeyboardRemove(),
    )
