
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.config import Config, RuntimeConfig
from core.i18n_translator import Translator
from core.schemas.message_payload import MessagePayload

from services import NotifierService
from ui.state_groups import AdminMenuSG, BannerMenuSG


@inject
async def get_banner_text(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    translator: FromDishka[Translator],
    notifier: FromDishka[NotifierService],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig]
):
    builder = InlineKeyboardBuilder()
    btn_text = translator.get_translated_text("channel_banner_btn")
    builder.button(text=btn_text, url=runtime_config.bot_url)

    if not message.text:
        return await manager.switch_to(
            BannerMenuSG.something_wrong,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
    
    payload = MessagePayload(
        i18n_key="channel_banner",
        i18n_kwargs={"text": message.text},
        reply_markup=builder.as_markup()
    )
    strategy = notifier.send_strategy_factory(config.CHANNEL_ID, payload)
    await notifier.send(strategy)
    
    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
