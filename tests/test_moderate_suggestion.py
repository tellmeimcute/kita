from unittest.mock import Mock
import pytest

from database.enums import SuggestionStatus
from usecases.moderate_suggestion import ModerateSuggestionUseCase


@pytest.mark.asyncio
async def test_accept_suggestion(suggestion_dto, suggestion_service_mock, notifier_mock, utils_mock, config_mock):
    usecase = ModerateSuggestionUseCase(
        config=config_mock,
        notifier=notifier_mock,
        utils=utils_mock,
        suggestion_service=suggestion_service_mock,
        i18n=Mock(),
    )

    result = await usecase.execute(suggestion_dto, verdict=SuggestionStatus.ACCEPTED)

    assert not result.verdict_exists
    assert suggestion_dto.status == SuggestionStatus.ACCEPTED
    suggestion_service_mock.update.assert_awaited_once_with(suggestion_dto)


@pytest.mark.asyncio
async def test_decline_suggestion(suggestion_dto, suggestion_service_mock, notifier_mock, utils_mock, config_mock):
    usecase = ModerateSuggestionUseCase(
        config=config_mock,
        notifier=notifier_mock,
        utils=utils_mock,
        suggestion_service=suggestion_service_mock,
        i18n=Mock(),
    )

    result = await usecase.execute(suggestion_dto, verdict=SuggestionStatus.DECLINED)

    assert not result.verdict_exists
    assert suggestion_dto.status == SuggestionStatus.DECLINED
    suggestion_service_mock.update.assert_awaited_once_with(suggestion_dto)


@pytest.mark.asyncio
async def test_verdict_already_exists(suggestion_dto, suggestion_service_mock, notifier_mock, utils_mock, config_mock):
    suggestion_dto.status = SuggestionStatus.ACCEPTED

    usecase = ModerateSuggestionUseCase(
        config=config_mock,
        notifier=notifier_mock,
        utils=utils_mock,
        suggestion_service=suggestion_service_mock,
        i18n=Mock(),
    )

    result = await usecase.execute(suggestion_dto, verdict=SuggestionStatus.DECLINED)

    assert result.verdict_exists
    assert suggestion_dto.status == SuggestionStatus.ACCEPTED
    suggestion_service_mock.update.assert_not_called()


@pytest.mark.asyncio
async def test_force_update_overwrites_existing_verdict(suggestion_dto, suggestion_service_mock, notifier_mock, utils_mock, config_mock):
    suggestion_dto.status = SuggestionStatus.ACCEPTED

    usecase = ModerateSuggestionUseCase(
        config=config_mock,
        notifier=notifier_mock,
        utils=utils_mock,
        suggestion_service=suggestion_service_mock,
        i18n=Mock(),
    )

    result = await usecase.execute(suggestion_dto, verdict=SuggestionStatus.DECLINED, force_update=True)

    assert not result.verdict_exists
    assert suggestion_dto.status == SuggestionStatus.DECLINED
    suggestion_service_mock.update.assert_awaited_once_with(suggestion_dto)
