from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import SecretStr

from core.exceptions import UserbotBanned, UserbotNotFoundError
from database.dto import UserBotDTO, UserDTO
from usecases.userbot import UserbotUseCase

USERBOT_ID = 666_000
BOT_TOKEN = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"


def make_userbot(*, owner_id: int, banned: bool = False) -> UserBotDTO:
    return UserBotDTO(
        token=SecretStr(BOT_TOKEN),
        bot_id=USERBOT_ID,
        username="test_userbot",
        owner_id=owner_id,
        active=True,
        banned=banned,
    )


@pytest.fixture
def userbot_service():
    return MagicMock(get=AsyncMock())


@pytest.fixture
def use_case(mock_bot_context, userbot_service) -> UserbotUseCase:
    uow = MagicMock()
    uow.transaction = MagicMock(return_value=AsyncMock())

    return UserbotUseCase(mock_bot_context, uow, userbot_service)


class TestUserbotUseCase:
    async def test_owner_gets_userbot(self, use_case, userbot_service, test_user_dto: UserDTO):
        userbot = make_userbot(owner_id=test_user_dto.user_id)
        userbot_service.get.return_value = userbot

        result = await use_case.execute(test_user_dto, USERBOT_ID)

        assert result is userbot
        userbot_service.get.assert_awaited_once_with(USERBOT_ID)

    async def test_missing_userbot(self, use_case, userbot_service, test_user_dto: UserDTO):
        userbot_service.get.return_value = None

        with pytest.raises(UserbotNotFoundError):
            await use_case.execute(test_user_dto, USERBOT_ID)

    async def test_foreign_userbot(
        self, use_case, userbot_service, test_user_dto: UserDTO, user_dto_factory
    ):
        stranger = user_dto_factory()
        userbot_service.get.return_value = make_userbot(owner_id=stranger.user_id)

        with pytest.raises(UserbotNotFoundError):
            await use_case.execute(test_user_dto, USERBOT_ID)

    async def test_banned_userbot(self, use_case, userbot_service, test_user_dto: UserDTO):
        userbot_service.get.return_value = make_userbot(
            owner_id=test_user_dto.user_id, banned=True
        )

        with pytest.raises(UserbotBanned):
            await use_case.execute(test_user_dto, USERBOT_ID)
