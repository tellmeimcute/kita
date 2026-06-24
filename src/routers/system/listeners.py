
import asyncio
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import I18n

from core.config import Config, RuntimeConfig
from core.schemas.message_payload import MessagePayload
from core.events import NewUserEvent, NewSuggestionEvent, SuggestionAcceptedEvent

from ui.suggestion_utils import SuggestionUtils
from services import NotifierService, UserService

logger = getLogger("kita.event")

async def notify_admin_new_user(event: NewUserEvent):
    config = await event.container.get(Config)

    session = await event.container.get(AsyncSession)
    user_service = await event.container.get(UserService)
    notifier = await event.container.get(NotifierService)
    i18n = await event.container.get(I18n)

    async with session.begin():
        admin = await user_service.get(config.admin_id)

    with i18n.context():
        with i18n.use_locale(admin.language_code):
            payload = MessagePayload(
                i18n_key="new_user_registered", 
                i18n_kwargs=dict(new_user_dto=event.user_dto.to_i18n_kwargs()),
            )
            await notifier.notify_user(admin, payload)

async def notify_admin_new_suggestion(event: NewSuggestionEvent):
    session = await event.container.get(AsyncSession)
    user_service = await event.container.get(UserService)
    notifier = await event.container.get(NotifierService)
    suggestion_utils = await event.container.get(SuggestionUtils)
    i18n = await event.container.get(I18n)

    async with session.begin():
        admins = await user_service.get_admins()

    with i18n.context():
        for admin in admins:
            with i18n.use_locale(admin.language_code):
                i18n_kwargs = suggestion_utils.get_i18n_kwargs(event.suggestion_dto)
                payload = MessagePayload(i18n_key="suggestion_notify_admin_new", i18n_kwargs=i18n_kwargs)
                await notifier.notify_user(admin, payload)
                await asyncio.sleep(0.2)

async def suggestion_accepted(event: SuggestionAcceptedEvent):
    config = await event.container.get(Config)
    runtime_config = await event.container.get(RuntimeConfig)
    notifier = await event.container.get(NotifierService)
    suggestion_utils = await event.container.get(SuggestionUtils)
    i18n = await event.container.get(I18n)

    with i18n.context():
        channel_payload = suggestion_utils.payload_factory(event.suggestion_dto, "channel_post_message")
        strategy = notifier.send_strategy_factory(config.channel_id, channel_payload)
        channel_post = await notifier.send(strategy)

        if isinstance(channel_post, list):
            channel_post = channel_post[0]
        post_url = channel_post.get_url() or runtime_config.bot_url
        
        with i18n.use_locale(event.suggestion_dto.author.language_code):
            author_payload = MessagePayload(
                i18n_key="notify_author_suggestion_posted", 
                i18n_kwargs=dict(post_url=post_url),
            )
            await notifier.notify_user(event.suggestion_dto.author, author_payload)
