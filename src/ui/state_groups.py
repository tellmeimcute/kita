
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

    user_select = State()
    user_moderation = State()

    app_stats = State()

    wait_broadcast_content = State()
    broadcast_confirm = State()