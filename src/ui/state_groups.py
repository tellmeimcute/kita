
from aiogram.filters.state import State, StatesGroup


class UserMenuSG(StatesGroup):
    main = State()
    settings = State()
    language = State()
    statistics = State()

    make_suggestion = State()
    suggestion_on_moderation = State()
    suggestion_media_error = State()


class AdminMenuSG(StatesGroup):
    main = State()

    app_stats = State()


class ModerationMenuSG(StatesGroup):
    user_select = State()
    user_select_again = State()
    user_moderation = State()


class BannerMenuSG(StatesGroup):
    prepare_banner = State()
    something_wrong = State()


class BroadcastMenuSG(StatesGroup):
    wait_broadcast_content = State()
    broadcast_confirm = State()