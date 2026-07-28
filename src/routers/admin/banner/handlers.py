
from aiogram.types import Message, Video, Animation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.config import Config
from core.i18n_translator import Translator

from database.dto import UserBotDTO
from ui.state_groups import AdminMenuSG


@inject
async def get_banner_text(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
    translator: FromDishka[Translator],
    config: FromDishka[Config],
    userbot_dto: FromDishka[UserBotDTO],
):
    builder = InlineKeyboardBuilder()
    btn_text = translator.translate("channel_banner_btn")
    builder.button(text=btn_text, url=userbot_dto.bot_url)
    markup = builder.as_markup()

    banner_text = message.text or message.caption
    media = message.video or message.photo or message.animation

    if not banner_text:
        manager.dialog_data["something_wrong"] = True
        return

    if isinstance(media, list):
        media = media[0]
        await message.bot.send_photo(
            userbot_dto.channel_id,
            photo=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif isinstance(media, Video):
        await message.bot.send_video(
            userbot_dto.channel_id,
            video=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif isinstance(media, Animation):
        await message.bot.send_animation(
            userbot_dto.channel_id,
            animation=media.file_id,
            caption=banner_text,
            reply_markup=markup,
        )
    elif not media:
        await message.bot.send_message(
            userbot_dto.channel_id,
            text=banner_text,
            reply_markup=markup,
        )

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
