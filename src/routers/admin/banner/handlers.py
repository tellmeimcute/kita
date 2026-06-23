
from aiogram.types import Message, Video, Animation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.config import Config, RuntimeConfig
from core.i18n_translator import Translator
from ui.state_groups import AdminMenuSG, BannerMenuSG


@inject
async def get_banner_text(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    translator: FromDishka[Translator],
    config: FromDishka[Config],
    runtime_config: FromDishka[RuntimeConfig]
):
    builder = InlineKeyboardBuilder()
    btn_text = translator.translate("channel_banner_btn")
    builder.button(text=btn_text, url=runtime_config.bot_url)
    markup = builder.as_markup()

    banner_text = message.text or message.caption
    media = message.video or message.photo or message.animation

    if not banner_text:
        return await manager.switch_to(
            BannerMenuSG.something_wrong,
            show_mode=ShowMode.DELETE_AND_SEND,
        )

    if isinstance(media, list):
        media = media[0]
        await message.bot.send_photo(
            config.channel_id,
            photo=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif isinstance(media, Video):
        await message.bot.send_video(
            config.channel_id,
            video=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif isinstance(media, Animation):
        await message.bot.send_animation(
            config.channel_id,
            animation=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif not media:
        await message.bot.send_message(
            config.channel_id,
            text=banner_text,
            reply_markup=markup,
        )

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
