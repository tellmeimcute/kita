import asyncio

from aiogram.types import Message
from aiogram.utils.i18n import I18n
from dishka.integrations.taskiq import FromDishka, inject

from database.dto import UserBotDTO
from interfaces import (
    MessageNotifierProtocol,
    SuggestionNotifierProtocol,
    SuggestionServiceProtocol,
    UserProfileServiceProtocol,
    UserServiceProtocol,
)
from task_queue.broker import broker
from utils.suggestion_utils import SuggestionUtils


@broker.task
@inject(patch_module=True)
async def admin_notify_new_suggestion(
    bot_id: int,
    suggestion_id: int,
    user_service: FromDishka[UserServiceProtocol],
    profile_service: FromDishka[UserProfileServiceProtocol],
    notifier: FromDishka[MessageNotifierProtocol],
    suggestion_utils: FromDishka[SuggestionUtils],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    i18n: FromDishka[I18n],
):
    admin_profiles = await profile_service.get_admins()
    suggestion = await suggestion_service.get(suggestion_id)

    with i18n.context():
        for profile in admin_profiles:
            admin_user = await user_service.get(profile.user_id)
            with i18n.use_locale(admin_user.language_code):
                i18n_kwargs = suggestion_utils.get_i18n_kwargs(suggestion)
                await notifier.send_text(admin_user, "suggestion_notify_admin_new", i18n_kwargs)
                await asyncio.sleep(0.2)


@broker.task
@inject(patch_module=True)
async def suggestion_accepted(
    bot_id: int,
    suggestion_id: int,
    userbot: FromDishka[UserBotDTO],
    notifier: FromDishka[MessageNotifierProtocol],
    suggestion_notifier: FromDishka[SuggestionNotifierProtocol],
    suggestion_service: FromDishka[SuggestionServiceProtocol],
    i18n: FromDishka[I18n],
):
    suggestion = await suggestion_service.get(suggestion_id)
    post_url = None

    with i18n.context():
        channel_post = await suggestion_notifier.send_to_channel(
            userbot.channel_id, suggestion
        )

        if isinstance(channel_post, list):
            channel_post = channel_post[0]
        if isinstance(channel_post, Message):
            post_url = channel_post.get_url()

        with i18n.use_locale(suggestion.author.language_code):
            await notifier.send_text(
                suggestion.author,
                "notify_author_suggestion_posted",
                i18n_kwargs={"post_url": post_url or userbot.bot_url},
            )


@broker.task
@inject(patch_module=True)
async def admin_notify_new_user(
    bot_id: int,
    new_user_id: int,
    userbot: FromDishka[UserBotDTO],
    notifier: FromDishka[MessageNotifierProtocol],
    user_service: FromDishka[UserServiceProtocol],
    i18n: FromDishka[I18n],
):
    admin = await user_service.get(userbot.owner_id)
    new_user = await user_service.get(new_user_id)

    with i18n.context(), i18n.use_locale(admin.language_code):
        i18n_kwargs = dict(new_user_dto=new_user.to_i18n_kwargs())
        await notifier.send_text(admin, "new_user_registered", i18n_kwargs=i18n_kwargs)
