
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dishka import FromDishka

from core.filters import I18nTextFilter, TextArgsFilter
from core.exceptions import UserImmuneError
from core.schemas.message_payload import MessagePayload
from core.schemas.viewer import SuggestionViewerData
from core.schemas import IDCommand

from database.dto import UserDTO
from database.enums import UserRole, SuggestionStatus
from interfaces import (
    UnitOfWorkProtocol,
    SuggestionServiceProtocol,
    NotifierServiceProtocol,
)

from usecases.moderate_suggestion import ModerateSuggestionUseCase
from usecases.change_role import ChangeRoleUseCase

from ui.state_groups import SuggestionViewerSG
from ui.suggestion_renderer import SuggestionRenderer


router = Router(name="admin_suggesions_soloview")


@router.message(TextArgsFilter("command_open_solo_view", IDCommand))
async def enter_soloview(
    message: Message,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    renderer: FromDishka[SuggestionRenderer],
    state: FSMContext,
    command: IDCommand,
):
    suggestion_dto = await suggestion_service.get(command.target_id)
    if not suggestion_dto:
        return await renderer.not_found(user_dto, command.target_id)

    await state.set_state(SuggestionViewerSG.in_solo_view)
    viewer_data.suggestion_dto = suggestion_dto
    await state.set_data({"viewer_data": viewer_data.model_dump(mode="json")})

    await renderer.suggestion(user_dto, suggestion_dto)
    await renderer.wait_verdict(user_dto)


@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("viewer_accept", verdict=SuggestionStatus.ACCEPTED))
@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("viewer_decline", verdict=SuggestionStatus.DECLINED))
async def soloview_verdict(
    message: Message,
    user_dto: UserDTO,
    state: FSMContext,
    uow: FromDishka[UnitOfWorkProtocol],
    viewer_data: FromDishka[SuggestionViewerData],
    moderation_usecase: FromDishka[ModerateSuggestionUseCase],
    renderer: FromDishka[SuggestionRenderer],
    verdict: SuggestionStatus,
):
    suggestion_dto = viewer_data.suggestion_dto
    async with uow.transaction():
        await moderation_usecase.execute(suggestion_dto, verdict, force_update=True)

    await renderer.verdict_rewrite(user_dto)
    await state.clear()


@router.message(SuggestionViewerSG.in_solo_view, I18nTextFilter("ban_btn"))
async def soloview_ban_author(
    message: Message,
    state: FSMContext,
    user_dto: UserDTO,
    viewer_data: FromDishka[SuggestionViewerData],
    uow: FromDishka[UnitOfWorkProtocol],
    notifier: FromDishka[NotifierServiceProtocol],
    renderer: FromDishka[SuggestionRenderer],
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
        payload = MessagePayload(i18n_key="error_user_immune")
        return await notifier.notify_user(user_dto, payload)

    await state.clear()
    await renderer.verdict_rewrite(user_dto)
