from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardMarkup

from services.notifier import MessageNotifier, NotifierUtilsMixin


class TestNotifierUtilsMixin:
    def test_parse_target_id_user_dto(self, test_user_dto):
        result = NotifierUtilsMixin()._parse_target_id(test_user_dto)
        assert result == test_user_dto.user_id

    def test_parse_target_id_user_profile_dto(self, test_profile_dto):
        result = NotifierUtilsMixin()._parse_target_id(test_profile_dto)
        assert result == test_profile_dto.user_id

    def test_parse_target_id_int(self):
        value = 67890
        result = NotifierUtilsMixin()._parse_target_id(value)
        assert result == value


@pytest.fixture
def notifier(mock_translator, mock_bot_registry) -> MessageNotifier:
    return MessageNotifier(translator=mock_translator, bot_registry=mock_bot_registry)


class TestMessageNotifier:
    async def test_send_text_targets_the_user_and_translates(
        self, notifier, test_user_dto, mock_translator
    ):
        mock_translator.i18n_text.return_value = "hello"

        await notifier.send_text(test_user_dto, "greeting", {"name": "Ann"})

        mock_translator.i18n_text.assert_called_once_with("greeting", {"name": "Ann"})
        notifier.bot.send_message.assert_awaited_once_with(
            chat_id=test_user_dto.user_id,
            text="hello",
            reply_markup=None,
            disable_notification=True,
            disable_web_page_preview=True,
        )

    async def test_send_text_accepts_a_raw_chat_id(self, notifier):
        chat_id = 67890

        await notifier.send_text(chat_id, "greeting")

        assert notifier.bot.send_message.await_args.kwargs["chat_id"] == chat_id

    async def test_forward_maps_the_target_to_the_destination_chat(self, notifier):
        source_chat = 111
        message_ids = [1, 2]

        await notifier.forward(222, source_chat, message_ids)

        notifier.bot.forward_messages.assert_awaited_once_with(
            chat_id=222,
            from_chat_id=source_chat,
            message_ids=message_ids,
        )

    async def test_edit_passes_the_keyboard_and_text(self, notifier):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        await notifier.edit(chat_id=42, message_id=7, new_text="new", new_kb=keyboard)

        notifier.bot.edit_message_text.assert_awaited_once_with(
            text="new",
            chat_id=42,
            message_id=7,
            reply_markup=keyboard,
        )


class TestNotifierExceptions:
    async def test_api_errors_are_not_swallowed(self, notifier):
        notifier.bot.send_message = AsyncMock(
            side_effect=TelegramAPIError(method=SendMessage(chat_id=1, text="x"), message="Bad")
        )

        with pytest.raises(TelegramAPIError):
            await notifier.send_text(1, "greeting")
