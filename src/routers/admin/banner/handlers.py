from aiogram.types import Animation, CallbackQuery, Message, Video
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from core.html import quote
from core.i18n_translator import Translator
from database.dto import UserBotDTO
from ui.state_groups import AdminMenuSG, BannerMenuSG


@inject
async def get_banner_text(
    message: Message,
    message_input: MessageInput,
    manager: DialogManager,
):
    banner_text = message.text or message.caption
    if not banner_text:
        manager.dialog_data["something_wrong"] = "banner_wait_for_text_again"
        return

    media = message.video or message.photo or message.animation

    media_type = None
    media_file_id = None

    if isinstance(media, list):
        media_type = "photo"
        media_file_id = media[-1].file_id
    elif isinstance(media, Video):
        media_type = "video"
        media_file_id = media.file_id
    elif isinstance(media, Animation):
        media_type = "animation"
        media_file_id = media.file_id

    manager.dialog_data["banner_media_type"] = media_type
    manager.dialog_data["banner_media_id"] = media_file_id
    manager.dialog_data["banner_text"] = banner_text

    await manager.switch_to(BannerMenuSG.confirm_banner, show_mode=ShowMode.DELETE_AND_SEND)


@inject
async def execute_banner(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    translator: FromDishka[Translator],
    userbot_dto: FromDishka[UserBotDTO],
):
    media_type = manager.dialog_data["banner_media_type"]
    media_file_id = manager.dialog_data["banner_media_id"]
    banner_text = manager.dialog_data["banner_text"]

    builder = InlineKeyboardBuilder()
    btn_text = translator.translate("channel_banner_btn")
    builder.button(text=btn_text, url=userbot_dto.bot_url)
    markup = builder.as_markup()

    text = quote(banner_text)

    if not media_type:
        await callback.bot.send_message(
            userbot_dto.channel_id,
            text=text,
            reply_markup=markup,
        )
    elif media_type == "photo":
        await callback.bot.send_photo(
            userbot_dto.channel_id,
            photo=media_file_id,
            caption=text,
            reply_markup=markup,
        )
    elif media_type == "video":
        await callback.bot.send_video(
            userbot_dto.channel_id,
            video=media_file_id,
            caption=text,
            reply_markup=markup,
        )
    elif media_type == "animation":
        await callback.bot.send_animation(
            userbot_dto.channel_id,
            animation=media_file_id,
            caption=text,
            reply_markup=markup,
        )

    await manager.start(AdminMenuSG.main, show_mode=ShowMode.DELETE_AND_SEND)
