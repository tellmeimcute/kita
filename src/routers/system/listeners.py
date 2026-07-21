
import asyncio
from logging import getLogger

from dishka import AsyncContainer
from aiogram.utils.i18n import I18n

from core.config import Config
from core.schemas import BotInfo
from core.events import NewUserEvent, NewSuggestionEvent, SuggestionAcceptedEvent, CopyMessagesToUserEvent
from interfaces import (
    UnitOfWorkProtocol,
    UserServiceProtocol,
    NotifierServiceProtocol,
)
from ui.suggestion_utils import SuggestionUtils


logger = getLogger("kita.event")

async def notify_admin_new_user(event: NewUserEvent, container: AsyncContainer):
    config = await container.get(Config)

    uow = await container.get(UnitOfWorkProtocol)
    user_service = await container.get(UserServiceProtocol)
    notifier = await container.get(NotifierServiceProtocol)
    i18n = await container.get(I18n)

    async with uow.transaction():
        admin = await user_service.get(config.admin_id)

    with i18n.context():
        with i18n.use_locale(admin.language_code):
            i18n_kwargs=dict(new_user_dto=event.user_dto.to_i18n_kwargs())
            await notifier.send_text(
                admin, "new_user_registered",
                i18n_kwargs=i18n_kwargs
            )

async def notify_admin_new_suggestion(event: NewSuggestionEvent, container: AsyncContainer):
    uow = await container.get(UnitOfWorkProtocol)
    user_service = await container.get(UserServiceProtocol)
    notifier = await container.get(NotifierServiceProtocol)
    suggestion_utils = await container.get(SuggestionUtils)
    i18n = await container.get(I18n)

    async with uow.transaction():
        admins = await user_service.get_admins()

    with i18n.context():
        for admin in admins:
            with i18n.use_locale(admin.language_code):
                i18n_kwargs = suggestion_utils.get_i18n_kwargs(event.suggestion_dto)
                await notifier.send_text(
                    admin, "suggestion_notify_admin_new",
                    i18n_kwargs=i18n_kwargs,
                )
                await asyncio.sleep(0.2)

async def suggestion_accepted(event: SuggestionAcceptedEvent, container: AsyncContainer):
    config = await container.get(Config)
    bot_info = await container.get(BotInfo)
    notifier = await container.get(NotifierServiceProtocol)
    i18n = await container.get(I18n)

    with i18n.context():
        channel_post = await notifier.send_suggestion(
            config.channel_id, event.suggestion_dto, mode="channel_post"
        )

        if isinstance(channel_post, list):
            channel_post = channel_post[0]
        
        post_url = bot_info.bot_url
        if channel_post:
            post_url = channel_post.get_url()
        
        with i18n.use_locale(event.suggestion_dto.author.language_code):
            await notifier.send_text(
                event.suggestion_dto.author, "notify_author_suggestion_posted",
                i18n_kwargs=dict(post_url=post_url),
            )

async def copy_to_user_notify_both(
    event: CopyMessagesToUserEvent, container: AsyncContainer
):
        notifier = await container.get(NotifierServiceProtocol)

        sent = await notifier.copy_messages(
            user_dto=event.user_dto, 
            messages=event.album_ids, 
            source=event.source_chat_id
        )
        
        await notifier.send_text(event.user_dto, "notify_you_receive_message")

        i18n_key = "message_delivered" if sent else "message_not_delivered"
        await notifier.send_text(event.caller_dto, i18n_key)
